"""Single-LLM in-turn tool loop driven by a ``PromptPlan``.

Extracted from ``agentic_loop`` so the orchestrator stays readable while this
module owns prompt-plan wire conversion, LangSmith accumulation, and interim
assistant persistence during tool rounds.
"""

from __future__ import annotations

import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from loguru import logger

from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    InTurnSyncToolLoopResult,
)
from app.core.companion_harness.companion.message_format import (
    openai_assistant_message_dict,
)
from app.core.companion_harness.companion.turn_routes import InTurnInterimOutput
from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.companion_harness.loop.context import AgenticLoopContext
from app.core.companion_harness.loop.in_turn_visible_text import (
    resolve_in_turn_assistant_visible_text,
)
from app.core.companion_harness.loop.runtime_system_clauses import (
    apply_agentic_loop_runtime_system_clauses,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompt_builder import (
    prompt_messages_to_openai_dicts,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call as repl_execute_tool_call,
)
from app.core.companion_harness.tools.runtime import (
    insert_openai_system_message,
    resolve_openai_tool_call_loop_async,
)
from app.core.companion_harness.companion.llm_chat_runtime import (
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from app.core.llms.client import AsyncLlmClient


@dataclass
class _PromptPlanToolLoopAccum:
    """Mutable LangSmith and transcript state across tool rounds."""

    langsmith_trace_acc: str
    langsmith_llm_run_acc: str
    loop_tools: list[dict[str, Any]]
    round_index: int = 0
    skip_final_transcript_assistant_row: bool = False
    last_interim_assistant_msg_uuid: str | None = None


async def _fetch_initial_prompt_plan_completion(
    *,
    context: AgenticLoopContext,
    llm_client: AsyncLlmClient,
    prompt_plan,
    chat_model: str,
    langsmith_extra: dict[str, Any],
    high_reasoning: bool,
) -> tuple[Any, list[dict[str, Any]], _PromptPlanToolLoopAccum]:
    request_messages = prompt_messages_to_openai_dicts(prompt_plan.messages)
    apply_agentic_loop_runtime_system_clauses(
        openai_messages=request_messages,
        user_text=context.user_text,
    )
    initial_resp = await llm_client.chat_completion(
        messages=request_messages,
        tools=list(prompt_plan.tools),
        tool_choice=prompt_plan.tool_choice,
        model=chat_model,
        langsmith_extra=langsmith_extra,
        high_reasoning=high_reasoning,
    )
    accum = _PromptPlanToolLoopAccum(
        langsmith_trace_acc=langsmith_trace_id_from_completion(initial_resp) or "",
        langsmith_llm_run_acc=langsmith_llm_run_id_from_completion(initial_resp)
        or "",
        loop_tools=list(prompt_plan.tools),
    )
    return initial_resp, deepcopy(request_messages), accum


def _make_prompt_plan_execute_tool_call(
    *,
    store: MemoryStore,
    allow: frozenset[str] | None,
    repository_only_store_text: bool,
) -> Callable[[str, str], Awaitable[tuple[str, str | None]]]:
    async def execute_tool_call(
        name: str, raw_arguments: str
    ) -> tuple[str, str | None]:
        result = await repl_execute_tool_call(
            store,
            name,
            raw_arguments,
            write_allowlist=allow,
            repository_only_store_text=repository_only_store_text,
        )
        return result, None

    return execute_tool_call


def _make_prompt_plan_continue_chat(
    *,
    llm_client: AsyncLlmClient,
    accum: _PromptPlanToolLoopAccum,
    prompt_plan,
    chat_model: str,
    langsmith_extra: dict[str, Any],
    high_reasoning: bool,
) -> Callable[
    [list[dict[str, Any]]], Awaitable[tuple[Any, str | None]]
]:
    async def continue_chat(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[Any, str | None]:
        next_resp = await llm_client.chat_completion(
            messages=messages_with_tool_results,
            tools=accum.loop_tools,
            tool_choice=prompt_plan.tool_choice,
            model=chat_model,
            langsmith_extra=langsmith_extra,
            high_reasoning=high_reasoning,
        )
        tid = langsmith_trace_id_from_completion(next_resp)
        rid = langsmith_llm_run_id_from_completion(next_resp)
        if tid:
            accum.langsmith_trace_acc = tid
        if rid:
            accum.langsmith_llm_run_acc = rid
        return next_resp, tid

    return continue_chat


def _make_prompt_plan_after_tool_messages(
    *,
    context: AgenticLoopContext,
    accum: _PromptPlanToolLoopAccum,
) -> Callable[[list[dict[str, Any]]], Awaitable[None]]:
    async def after_tool_messages_appended(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> None:
        if context.after_tool_messages_appended is None:
            return
        refreshed = await context.after_tool_messages_appended(
            messages_with_tool_results
        )
        if refreshed is not None:
            accum.loop_tools = refreshed

    return after_tool_messages_appended


def _make_prompt_plan_on_assistant_message(
    *,
    store: MemoryStore,
    context: AgenticLoopContext,
    accum: _PromptPlanToolLoopAccum,
    interim_output_sink,
    emit_every_round: bool,
) -> Callable[[Any], Awaitable[None]]:
    transcript_rel = context.transcript_rel
    trace_id = context.trace_id
    user_msg_uuid = context.user_msg_uuid

    async def on_assistant_message(message: Any) -> None:
        accum.round_index += 1
        body = resolve_in_turn_assistant_visible_text(message)
        if body is None:
            had_tool_calls_early = bool(
                getattr(message, "tool_calls", None) or []
            )
            if had_tool_calls_early:
                logger.warning(
                    "in_turn_visible_text_missing trace_id={} round_index={}",
                    trace_id,
                    accum.round_index,
                )
            return
        had_tool_calls = bool(
            (
                message.get("tool_calls")
                if isinstance(message, dict)
                else getattr(message, "tool_calls", None)
            )
            or []
        )
        assistant_msg_uuid = str(uuid.uuid4())
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
        accum.last_interim_assistant_msg_uuid = assistant_msg_uuid
        if not had_tool_calls:
            accum.skip_final_transcript_assistant_row = True
        if interim_output_sink is not None and (
            emit_every_round or had_tool_calls
        ):
            await interim_output_sink(
                InTurnInterimOutput(
                    text=body,
                    user_msg_uuid=user_msg_uuid,
                    trace_id=trace_id,
                    langsmith_trace_id=accum.langsmith_trace_acc,
                    langsmith_run_id=accum.langsmith_llm_run_acc,
                    round_index=accum.round_index,
                    had_tool_calls=had_tool_calls,
                    assistant_msg_uuid=assistant_msg_uuid,
                )
            )

    return on_assistant_message


async def run_prompt_plan_tool_loop(
    context: AgenticLoopContext,
    *,
    store: MemoryStore,
    llm_client: AsyncLlmClient,
    interim_output_sink,
    max_tool_call_rounds: int,
) -> InTurnSyncToolLoopResult:
    """Single-LLM tool loop using ``PromptPlan`` wire messages owned by this loop.

    TODO(#3629): Stop converting PromptPlan to wire dicts here; pass plan into AsyncLlmClient.
    TODO(#3630): Build langsmith_extra from LlmInvocationContext, not call-site dicts.
    """
    assert context.prompt_plan is not None
    execution = context.execution
    prompt_plan = context.prompt_plan
    chat_model = llm_client.resolve_model("chat")
    langsmith_extra = context.langsmith.turn_slice.foreground_invocation_extra(
        source=execution.foreground_source.value,
        extra_metadata=None,
    )
    t_api = time.perf_counter()
    initial_resp, working_messages, accum = (
        await _fetch_initial_prompt_plan_completion(
            context=context,
            llm_client=llm_client,
            prompt_plan=prompt_plan,
            chat_model=chat_model,
            langsmith_extra=langsmith_extra,
            high_reasoning=execution.high_reasoning,
        )
    )
    loop_result = await resolve_openai_tool_call_loop_async(
        response=initial_resp,
        openai_messages=working_messages,
        max_tool_call_rounds=max_tool_call_rounds,
        execute_tool_call=_make_prompt_plan_execute_tool_call(
            store=store,
            allow=execution.write_allowlist,
            repository_only_store_text=context.repository_only_store_text,
        ),
        continue_chat=_make_prompt_plan_continue_chat(
            llm_client=llm_client,
            accum=accum,
            prompt_plan=prompt_plan,
            chat_model=chat_model,
            langsmith_extra=langsmith_extra,
            high_reasoning=execution.high_reasoning,
        ),
        build_assistant_tool_call_message=openai_assistant_message_dict,
        insert_system_message=insert_openai_system_message,
        initial_trace_id=accum.langsmith_trace_acc or None,
        after_tool_messages_appended=_make_prompt_plan_after_tool_messages(
            context=context,
            accum=accum,
        ),
        on_assistant_message=_make_prompt_plan_on_assistant_message(
            store=store,
            context=context,
            accum=accum,
            interim_output_sink=interim_output_sink,
            emit_every_round=True,
        ),
    )
    if loop_result.trace_id:
        accum.langsmith_trace_acc = loop_result.trace_id
    final_msg = loop_result.response.choices[0].message
    last_text = (final_msg.content or "").strip()
    approx_ctx_chars = sum(
        len(str(m.get("content") or "")) for m in loop_result.messages
    )
    logger.info(
        "prompt_plan_tool_loop llm_done model={} chat_completions_ms={:.0f} "
        "approx_ctx_chars={} trace_id={}",
        chat_model,
        (time.perf_counter() - t_api) * 1000.0,
        approx_ctx_chars,
        context.trace_id,
    )
    return InTurnSyncToolLoopResult(
        assistant_text=last_text,
        langsmith_trace_id=accum.langsmith_trace_acc,
        langsmith_run_id=accum.langsmith_llm_run_acc,
        skip_final_transcript_assistant_row=accum.skip_final_transcript_assistant_row,
        last_interim_assistant_msg_uuid=accum.last_interim_assistant_msg_uuid,
        loop_persisted_user_transcript=True,
    )
