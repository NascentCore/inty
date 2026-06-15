"""In-turn synchronous chat + tool loop (single LLM, no dual-LLM / tool_background).

Used by ``USER_CHAT_BOOTSTRAP`` today; future settled ``USER_CHAT`` in-turn sync (#3369) reuses
the same entry with different ``write_allowlist`` / ``after_tool_messages_appended`` hooks.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger

from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call as repl_execute_tool_call,
)
from app.core.companion_harness.tools.runtime import (
    insert_openai_system_message,
    resolve_openai_tool_call_loop_async,
)
from .langsmith_turn_slice import CompanionTurnLangsmithSlice
from .llm_client import CompanionLLMClient, LLM_SCENE_CHAT
from .llm_chat_runtime import (
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from .message_format import openai_assistant_message_dict
from .models import CompanionTurnTrack, InnerTickActivity
from .prompt_stack import refresh_companion_turn_prompt_stack
from .turn_routes import BootstrapInterimOutput, BootstrapInterimOutputSink
from .utc import utc_iso_ts

BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS = 24


@dataclass(frozen=True)
class InTurnSyncToolLoopInput:
    """Inputs for one in-turn sync tool loop."""

    store: MemoryStore
    llm_client: CompanionLLMClient
    messages: tuple[dict[str, Any], ...]
    tools_for_turn: tuple[dict[str, Any], ...]
    write_allowlist: frozenset[str]
    langsmith_foreground_source: str
    repository_only_store_text: bool
    trace_id: str
    user_text: str
    ts_user: datetime
    user_msg_uuid: str
    transcript_rel: str
    # TODO(#3369): Rename ``BootstrapInterimOutputSink`` when settled USER_CHAT reuses this loop.
    interim_output_sink: BootstrapInterimOutputSink | None
    skip_inline_interim_transcript: bool
    langsmith_slice: CompanionTurnLangsmithSlice
    max_tool_rounds: int
    # Runs after each tool round (same timing as ``runtime.after_tool_messages_appended``).
    # Hook may mutate ``messages`` in place; an optional return value replaces the OpenAI
    # ``tools`` list for subsequent LLM rounds (see ``refresh_companion_turn_prompt_stack``).
    after_tool_messages_appended: (
        Callable[
            [list[dict[str, Any]]],
            Awaitable[list[dict[str, Any]] | None],
        ]
        | None
    )


@dataclass(frozen=True)
class InTurnSyncToolLoopResult:
    """Outputs from one in-turn sync tool loop."""

    assistant_text: str
    langsmith_trace_id: str
    langsmith_run_id: str
    skip_final_transcript_assistant_row: bool
    last_interim_assistant_msg_uuid: str | None


@dataclass(frozen=True)
class BootstrapInTurnSyncToolLoopInput:
    """Bootstrap-track inputs for :func:`run_bootstrap_track_sync_tool_loop`.

    TODO(#3398): Collapse shared fields into ``InTurnSyncToolLoopInput`` via a builder
    once bootstrap and settled USER_CHAT share the same call site shape.
    """

    store: MemoryStore
    llm_client: CompanionLLMClient
    messages: tuple[dict[str, Any], ...]
    tools_for_turn: tuple[dict[str, Any], ...]
    memory_bootstrap_type: str
    repository_only_store_text: bool
    trace_id: str
    user_text: str
    ts_user: datetime
    user_msg_uuid: str
    transcript_rel: str
    bootstrap_interim_output_sink: BootstrapInterimOutputSink | None
    langsmith_slice: CompanionTurnLangsmithSlice


async def run_in_turn_sync_tool_loop(
    loop_input: InTurnSyncToolLoopInput,
) -> InTurnSyncToolLoopResult:
    """In-turn chat + tools on one chat model (no dual-LLM / tool_background).

    Persists the user transcript row first, then non-empty assistant ``content`` from each LLM
    round (via callback) so JSONL order is always user → assistant(s). Interim rounds with
    ``tool_calls`` may also push via ``interim_output_sink``. Caller must not append
    the user row again at turn end.
    """
    store = loop_input.store
    transcript_rel = loop_input.transcript_rel
    trace_id = loop_input.trace_id
    user_msg_uuid = loop_input.user_msg_uuid
    store.append_jsonl_record(
        transcript_rel,
        {
            "role": "user",
            "content": loop_input.user_text,
            "ts": loop_input.ts_user.isoformat(),
            "uuid": user_msg_uuid,
            "trace_id": trace_id,
        },
    )
    working_messages = deepcopy(list(loop_input.messages))
    loop_tools = list(loop_input.tools_for_turn)
    chat_model = loop_input.llm_client.resolve_model("chat")
    allow = loop_input.write_allowlist
    langsmith_slice = loop_input.langsmith_slice
    foreground_source = loop_input.langsmith_foreground_source

    def _chat_sync(
        msgs: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> Any:
        return loop_input.llm_client.chat_completion(
            messages=msgs,
            model=chat_model,
            tools=tools,
            scene=LLM_SCENE_CHAT,
            langsmith_extra=langsmith_slice.foreground_invocation_extra(
                source=foreground_source,
                extra_metadata=None,
            ),
        )

    t_api = time.perf_counter()
    initial_resp = await asyncio.to_thread(
        _chat_sync, working_messages, loop_tools
    )
    langsmith_trace_acc = langsmith_trace_id_from_completion(initial_resp) or ""
    langsmith_llm_run_acc = (
        langsmith_llm_run_id_from_completion(initial_resp) or ""
    )

    async def execute_tool_call(
        name: str, raw_arguments: str
    ) -> tuple[str, str | None]:
        result = await repl_execute_tool_call(
            store,
            name,
            raw_arguments,
            write_allowlist=allow,
            repository_only_store_text=loop_input.repository_only_store_text,
        )
        return result, None

    async def continue_chat(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[Any, str | None]:
        next_resp = await asyncio.to_thread(
            _chat_sync, messages_with_tool_results, loop_tools
        )
        nonlocal langsmith_trace_acc, langsmith_llm_run_acc
        tid = langsmith_trace_id_from_completion(next_resp)
        rid = langsmith_llm_run_id_from_completion(next_resp)
        if tid:
            langsmith_trace_acc = tid
        if rid:
            langsmith_llm_run_acc = rid
        return next_resp, tid

    async def _after_tool_messages_appended(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> None:
        nonlocal loop_tools
        if loop_input.after_tool_messages_appended is not None:
            refreshed = await loop_input.after_tool_messages_appended(
                messages_with_tool_results
            )
            if refreshed is not None:
                loop_tools = refreshed

    round_index = 0
    skip_final_transcript_assistant_row = False
    last_interim_assistant_msg_uuid: str | None = None
    interim_sink = loop_input.interim_output_sink

    async def _on_assistant_message(message: Any) -> None:
        nonlocal round_index
        nonlocal langsmith_trace_acc
        nonlocal langsmith_llm_run_acc
        nonlocal skip_final_transcript_assistant_row
        nonlocal last_interim_assistant_msg_uuid
        round_index += 1
        body = (message.content or "").strip()
        if not body:
            return
        had_tool_calls = bool(getattr(message, "tool_calls", None) or [])
        ls_trace = langsmith_trace_acc
        ls_run = langsmith_llm_run_acc
        assistant_msg_uuid = str(uuid.uuid4())
        if not loop_input.skip_inline_interim_transcript:
            store.append_jsonl_record(
                transcript_rel,
                {
                    "role": "assistant",
                    "content": body,
                    "ts": utc_iso_ts(),
                    "uuid": assistant_msg_uuid,
                    "reply_to": user_msg_uuid,
                    "source": "chat",
                    "trace_id": trace_id,
                },
            )
        last_interim_assistant_msg_uuid = assistant_msg_uuid
        if not had_tool_calls:
            skip_final_transcript_assistant_row = True
        if interim_sink is not None and had_tool_calls:
            await interim_sink(
                BootstrapInterimOutput(
                    text=body,
                    user_msg_uuid=user_msg_uuid,
                    trace_id=trace_id,
                    langsmith_trace_id=ls_trace,
                    langsmith_run_id=ls_run,
                    round_index=round_index,
                    had_tool_calls=had_tool_calls,
                    assistant_msg_uuid=assistant_msg_uuid,
                )
            )

    loop_result = await resolve_openai_tool_call_loop_async(
        response=initial_resp,
        openai_messages=working_messages,
        max_tool_call_rounds=loop_input.max_tool_rounds,
        execute_tool_call=execute_tool_call,
        continue_chat=continue_chat,
        build_assistant_tool_call_message=openai_assistant_message_dict,
        insert_system_message=insert_openai_system_message,
        initial_trace_id=langsmith_trace_acc or None,
        after_tool_messages_appended=_after_tool_messages_appended,
        on_assistant_message=_on_assistant_message,
    )
    if loop_result.trace_id:
        langsmith_trace_acc = loop_result.trace_id
    final_msg = loop_result.response.choices[0].message
    last_text = (final_msg.content or "").strip()
    approx_ctx_chars = sum(
        len(str(m.get("content") or "")) for m in loop_result.messages
    )
    logger.info(
        "in_turn_sync_tool_loop llm_done model={} chat_completions_ms={:.0f} "
        "approx_ctx_chars={} trace_id={}",
        chat_model,
        (time.perf_counter() - t_api) * 1000.0,
        approx_ctx_chars,
        trace_id,
    )
    return InTurnSyncToolLoopResult(
        assistant_text=last_text,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_llm_run_acc,
        skip_final_transcript_assistant_row=skip_final_transcript_assistant_row,
        last_interim_assistant_msg_uuid=last_interim_assistant_msg_uuid,
    )


async def run_bootstrap_track_sync_tool_loop(
    loop_input: BootstrapInTurnSyncToolLoopInput,
) -> InTurnSyncToolLoopResult:
    """Bootstrap track wrapper around :func:`run_in_turn_sync_tool_loop`."""
    from app.core.companion_harness.tools.companion_tool_definitions import (
        MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
    )

    store = loop_input.store
    memory_bootstrap_type = loop_input.memory_bootstrap_type

    async def _bootstrap_after_tool_round(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return refresh_companion_turn_prompt_stack(
            store=store,
            memory_bootstrap_type=memory_bootstrap_type,
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            messages=messages_with_tool_results,
            track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        )

    result = await run_in_turn_sync_tool_loop(
        InTurnSyncToolLoopInput(
            store=store,
            llm_client=loop_input.llm_client,
            messages=loop_input.messages,
            tools_for_turn=loop_input.tools_for_turn,
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
            langsmith_foreground_source=SOURCE_BOOTSTRAP_TRACK,
            repository_only_store_text=loop_input.repository_only_store_text,
            trace_id=loop_input.trace_id,
            user_text=loop_input.user_text,
            ts_user=loop_input.ts_user,
            user_msg_uuid=loop_input.user_msg_uuid,
            transcript_rel=loop_input.transcript_rel,
            interim_output_sink=loop_input.bootstrap_interim_output_sink,
            skip_inline_interim_transcript=False,
            langsmith_slice=loop_input.langsmith_slice,
            max_tool_rounds=BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
            after_tool_messages_appended=_bootstrap_after_tool_round,
        )
    )
    logger.info(
        "run_turn bootstrap_track llm_done assistant_chars={} trace_id={}",
        len(result.assistant_text),
        loop_input.trace_id,
    )
    return result
