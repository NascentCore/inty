"""Background tool execution queue for async dual-LLM mode.

Persists tool return strings under a ``--- Tool results ---`` section on ``source=tool_bg``
transcript rows so the following ``run_turn`` sees them in chat/tool message assembly.
Optional ``tool_bg_idle_event`` coordinates per-session ordering with ``turn.run_turn``.

TODO(tool-bg-idle-starves-user-chat): If the background thread never reaches ``finally`` — #3123
below, ``tool_bg_idle`` stays cleared and ``run_turn`` on user/proactive turns blocks
behind ``turn_lock`` (monolog inner-tick is the common trigger). Intended: watchdog,
cancel, or always release idle on thread exit.
Issues: https://github.com/NascentCore/inty/issues/3123,
https://github.com/NascentCore/inty/issues/3113.

TODO(#3631): Use AsyncLlmClient instead of asyncio.to_thread(chat_completion_sync, ...).
"""

from __future__ import annotations

import asyncio
import re
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Protocol

from loguru import logger
from openai import BadRequestError

from app.utils.models_catalog import GenAIModel

from app.core.companion_harness.llm.langsmith_invocation_extra import (
    INTY_TOOL_BG_ROUND_METADATA_KEY,
    SOURCE_TOOL_BACKGROUND_CONTINUE,
    SOURCE_TOOL_BACKGROUND_INITIAL,
    tool_choice_attempt_metadata,
)
from app.core.companion_harness.llm.ports import ChatCompletionsSyncPort
from app.core.companion_harness.tools.runtime import (
    insert_openai_system_message,
    resolve_openai_tool_call_loop_async,
)

from app.core.companion_harness.companion.llm_chat_runtime import (
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from app.core.companion_harness.companion.llm_runtime_events import (
    record_llm_inference_failure,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    transcript_relative_path_for_turn_persistence,
)
from app.core.companion_harness.companion.prompt_stack import (
    refresh_companion_turn_prompt_stack,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    envelope_to_assistant_metadata_dict,
    turn_recall_from_envelope,
)
from app.core.companion_harness.companion.transcript_assistant_row import (
    TranscriptAssistantRowBuildInput,
    append_transcript_assistant_row,
)
from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.companion_harness.companion.message_format import (
    openai_assistant_message_dict,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    TOOL_BACKGROUND_JSONL_REL,
)

from .companion_tool_definitions import MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST
from .companion_tool_runtime import (
    round_includes_generation_tool,
    tool_requires_client_delivery_on_success,
)
from .image_gate import list_image_asset_records
from .tool_bg_routing import resolve_tool_background_finish_envelope

_ABORT_TOOL_BG_LOCK = threading.Lock()
_ABORTED_TOOL_BG_USER_MSG_UUIDS: set[str] = set()
_BG_TOOL_MAX_ROUNDS = 24

# Persisted on ``source=tool_bg`` transcript rows so the next turn's chat/tool LLMs
# reliably see raw tool return strings (even when routing NL is non-empty).
TOOL_RESULTS_TRANSCRIPT_MARKER = "--- Tool results ---"


class ToolBackgroundTraceHooks(Protocol):
    """Optional REPL-side hooks for LLM round tracing (e.g. LangSmith); kernel stays import-free."""

    def on_tool_path_llm_round(
        self,
        *,
        round_idx: int,
        model: str,
        request_messages: list[dict[str, Any]],
        response: Any,
        scope_registry_key: str,
        trace_id: str | None,
    ) -> None: ...


def is_tool_background_aborted(user_msg_uuid: str) -> bool:
    with _ABORT_TOOL_BG_LOCK:
        return user_msg_uuid in _ABORTED_TOOL_BG_USER_MSG_UUIDS


def clear_tool_background_abort_flag(user_msg_uuid: str) -> None:
    with _ABORT_TOOL_BG_LOCK:
        _ABORTED_TOOL_BG_USER_MSG_UUIDS.discard(user_msg_uuid)


class BackgroundToolLoopAborted(Exception):
    """User superseded REPL turn; exit background tool loop without transcript side effects."""


# Fal `generate_image` / `modify_image` tool summaries include `local_path=/abs/path/...`.
_LOCAL_PATH_IN_TOOL = re.compile(r"local_path=(\S+)")
# First tool_background completion tries tool_choice=required whenever the OpenAI tools list
# is non-empty; BadRequest fallbacks omit it (provider auto mode).


def _local_paths_from_tool_messages(
    messages: list[dict[str, Any]],
) -> list[str]:
    """Collect absolute paths from tool role messages (dedupe, order preserved)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in messages:
        if m.get("role") != "tool":
            continue
        content = m.get("content")
        if not isinstance(content, str):
            continue
        for match in _LOCAL_PATH_IN_TOOL.finditer(content):
            p = match.group(1)
            if p and p != "(none)" and p not in seen:
                seen.add(p)
                out.append(p)
    return out


def _extract_tool_call_names(messages: list[dict[str, Any]]) -> list[str]:
    """Collect tool function names from assistant tool_call messages in order."""
    names: list[str] = []
    for m in messages:
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function")
            if not isinstance(fn, dict):
                continue
            raw = fn.get("name")
            if isinstance(raw, str):
                n = raw.strip()
                if n:
                    names.append(n)
    return names


def build_tool_background_transcript_body(
    *,
    display_text: str,
    appended_turn_msgs: list[dict[str, Any]],
    total_tool_calls: int,
) -> str:
    """NL visible to user (routing) plus a fixed marker section of tool return strings."""
    nl = (display_text or "").strip()
    digest_core = ""
    if total_tool_calls > 0:
        digest_core = _tool_bg_nl_filler_from_appended_turn(
            appended_turn_msgs
        ).strip()
    digest_block = ""
    if digest_core:
        digest_block = f"{TOOL_RESULTS_TRANSCRIPT_MARKER}\n{digest_core}"
    if nl and digest_block:
        return f"{nl}\n\n{digest_block}"
    return nl or digest_block


def _tool_bg_nl_filler_from_appended_turn(
    appended_messages: list[dict[str, Any]],
) -> str:
    """Concatenate non-error tool string results when NL summary is empty but output_to_user is true."""
    chunks: list[str] = []
    max_chunks = 8
    max_chars = 8000
    total = 0
    for m in appended_messages:
        role = m.get("role")
        if role == "assistant":
            continue
        if role != "tool":
            continue
        tid = m.get("tool_call_id")
        if not isinstance(tid, str):
            continue
        content = m.get("content")
        if not isinstance(content, str):
            continue
        piece = content.strip()
        if not piece or piece.startswith("ERROR"):
            continue
        if len(chunks) >= max_chunks:
            break
        if total + len(piece) > max_chars:
            piece = piece[: max(0, max_chars - total - 1)] + "..."
        chunks.append(piece)
        total += len(piece)
    return "\n".join(chunks)


def _generation_tool_execution_deliver(
    appended_messages: list[dict[str, Any]],
    tool_call_names: list[str],
    image_paths: list[str],
) -> bool:
    """
    GENERATION tools must reach the client only when execution succeeded (paths or non-ERROR tool text).
    """
    if not round_includes_generation_tool(tool_call_names):
        return False
    if image_paths:
        return True
    pending: dict[str, str] = {}
    for m in appended_messages:
        if m.get("role") == "assistant":
            pending.clear()
            for tc in m.get("tool_calls") or []:
                if not isinstance(tc, dict):
                    continue
                tid = tc.get("id")
                fn = tc.get("function")
                if not isinstance(fn, dict):
                    continue
                raw_name = fn.get("name")
                if isinstance(tid, str) and isinstance(raw_name, str):
                    n = raw_name.strip()
                    if n:
                        pending[tid] = n
            continue
        if m.get("role") != "tool":
            continue
        tid = m.get("tool_call_id")
        if not isinstance(tid, str):
            continue
        name = pending.get(tid)
        if not name or not tool_requires_client_delivery_on_success(name):
            continue
        content = str(m.get("content") or "").strip()
        if content.startswith("ERROR"):
            continue
        if content:
            return True
    return False


def tool_background_should_deliver_to_user(
    *,
    suppress_user_delivery: bool,
    generation_deliver: bool,
    output_to_user: bool,
) -> bool:
    """Whether ``tool_background`` may emit a client-visible ``ToolOutputEvent``."""
    if suppress_user_delivery:
        return False
    return generation_deliver or output_to_user


@dataclass(frozen=True)
class ToolOutputEvent:
    scope_registry_key: str
    memory_store: MemoryStore
    user_msg_uuid: str
    assistant_msg_uuid: str
    text: str
    ts: str
    elapsed_ms: int
    trace_id: str = (
        ""  # run_turn turn id; links transcript rows + tool_background_done
    )
    langsmith_trace_id: str = ""
    langsmith_run_id: str = ""
    output_to_user: bool = False
    generation_deliver: bool = False
    image_asset_baseline: int = 0
    # Absolute on-disk paths for images created during this background tool round.
    # Surfaced to REPL via meta_data.tool_bg_local_image_paths; production clients ignore.
    local_image_paths: tuple[str, ...] = ()
    # Parsed from unified finish envelope; mirrors foreground significance_perception shape.
    significance_perception: dict[str, Any] | None = None
    turn_recall: str | None = None
    # InnerTickActivity.value when this background round is an inner-tick turn; else None.
    inner_tick_activity: str | None = None


def _assistant_text_from_completion_response(resp: Any) -> str:
    # TODO(companion-dual-envelope-reasoning-channel): Tool-background path only reads ``.content``; — #3398
    # same provider quirk as foreground ``turn.py`` when switching reasoning-heavy chat models.
    # TODO(#3398): dual-LLM tool-model leg; epic tracks single-LLM in-turn alternative for user chat.
    content = resp.choices[0].message.content
    if not isinstance(content, str):
        preview = repr(content)
        if len(preview) > 500:
            preview = preview[:500] + "..."
        logger.warning(
            "tool_background completion assistant message.content is not str "
            "type={} preview={}",
            type(content).__name__,
            preview,
        )
        return ""
    return content.strip()


def _single_line_log_preview(text: str, max_chars: int = 280) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 3] + "..."


@dataclass(frozen=True)
class _InitialToolBgCompletionMeta:
    """Winning attempt parameters for tool_background first completion."""

    tool_choice: str | None


def _initial_tool_bg_completion_with_fallbacks(
    client: Any,
    chat_completion_sync: ChatCompletionsSyncPort,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
    force_tools: bool,
    langsmith_slice: CompanionTurnLangsmithSlice,
) -> tuple[Any, _InitialToolBgCompletionMeta]:
    """
    First tool_background completion (no response_format; tools may use tool_choice fallbacks).

    Returns (response, meta for last_chat_completion_request snapshot).
    """
    attempts: list[str | None] = []
    if force_tools:
        attempts.append("required")
    attempts.append(None)

    last_br: BadRequestError | None = None
    for tc in attempts:
        try:
            resp = chat_completion_sync(
                client,
                model=model,
                messages_payload=messages_payload,
                tools=tools,
                tool_choice=tc,
                response_format=None,
                langsmith_extra=langsmith_slice.tool_call_extra(
                    phase_suffix=SOURCE_TOOL_BACKGROUND_INITIAL,
                    extra_metadata=tool_choice_attempt_metadata(tc),
                ),
                high_reasoning=True,
            )
            meta = _InitialToolBgCompletionMeta(tool_choice=tc)
            return resp, meta
        except BadRequestError as exc:
            last_br = exc
            logger.warning(
                "repl.turn.bg initial_completion BadRequest tool_choice={} err={}",
                tc,
                exc,
            )
            continue
    if last_br is not None:
        raise last_br
    raise RuntimeError("tool_background initial completion: empty attempts")


def _openai_messages_payload(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {k: v for k, v in m.items() if not k.startswith("_")} for m in messages
    ]


def _log_bg_llm_round_result(
    *,
    round_idx: int,
    model: str,
    resp: Any,
    request_messages: list[dict[str, Any]],
    scope_registry_key: str,
    trace_id: str | None = None,
    trace_hooks: ToolBackgroundTraceHooks | None = None,
) -> None:
    ch0 = resp.choices[0]
    fr = getattr(ch0, "finish_reason", None) or "?"
    tool_calls = getattr(ch0.message, "tool_calls", None) or []
    logger.info(
        "repl.turn.bg llm_round={} finish_reason={} tool_calls_n={} model={}",
        round_idx,
        fr,
        len(tool_calls),
        model,
    )
    if trace_hooks is not None:
        trace_hooks.on_tool_path_llm_round(
            round_idx=round_idx,
            model=model,
            request_messages=request_messages,
            response=resp,
            scope_registry_key=scope_registry_key,
            trace_id=trace_id,
        )


def _append_background_transcript_assistant(
    *,
    store: MemoryStore,
    content: str,
    assistant_msg_uuid: str,
    reply_to: str,
    trace_id: str,
    transcript_relative_path: str,
    significance_perception: dict[str, Any] | None = None,
    turn_recall: str | None = None,
) -> None:
    append_transcript_assistant_row(
        store,
        transcript_relative_path,
        TranscriptAssistantRowBuildInput(
            content=content,
            uuid=assistant_msg_uuid,
            reply_to=reply_to,
            trace_id=trace_id,
            source="tool_bg",
            significance_perception=significance_perception,
            turn_recall=turn_recall,
        ),
        ts=utc_iso_ts(),
    )


@dataclass
class ToolBgLoopProgress:
    """Mutable counters for one background tool loop."""

    rounds_used: int
    active_round: int
    total_tool_calls: int


@dataclass
class ToolBgTurnCapture:
    """Tool-round message rows captured before system refresh."""

    appended_turn_msgs: list[dict[str, Any]]
    capture_from_len: int


@dataclass
class _ToolBgOpenAiLoopHandlers:
    """Callbacks and capture state for ``resolve_openai_tool_call_loop_async``."""

    execute_tool_call: Callable[[str, str], Any]
    continue_chat: Callable[[list[dict[str, Any]]], Any]
    after_tool_messages_appended: Callable[[list[dict[str, Any]]], Any]
    turn_capture: ToolBgTurnCapture
    tools_for_rounds: list[Any]


@dataclass(frozen=True)
class ToolBgDeliveryPlan:
    """Resolved user-visible delivery for one background tool loop."""

    should_push: bool
    deliver_output_to_user: bool
    display_text: str
    transcript_body: str
    significance_meta: dict[str, Any] | None
    turn_recall: str | None
    output_to_user_flag: bool
    generation_deliver: bool
    tool_call_names: list[str]
    image_paths: list[str]
    bg_ls_trace: str
    bg_ls_llm_run: str


def _append_background_log(
    *,
    store: MemoryStore,
    user_msg_uuid: str,
    assistant_msg_uuid: str,
    elapsed_ms: int,
    rounds: int,
    tool_calls_count: int,
    generated_image_uris: list[str],
    trace_id: str = "",
) -> None:
    row: dict[str, Any] = {
        "kind": "tool_background_done",
        "ts": utc_iso_ts(),
        "user_msg_uuid": user_msg_uuid,
        "assistant_msg_uuid": assistant_msg_uuid,
        "elapsed_ms": elapsed_ms,
        "rounds": rounds,
        "tool_calls_count": tool_calls_count,
        "generated_image_uris": list(generated_image_uris),
    }
    if trace_id.strip():
        row["trace_id"] = trace_id
    store.append_jsonl_record(
        TOOL_BACKGROUND_JSONL_REL,
        row,
    )


async def _fetch_tool_bg_initial_completion(
    *,
    resolved_client: Any,
    chat_completion_sync: ChatCompletionsSyncPort,
    working_messages: list[dict[str, Any]],
    tools: list[Any],
    tool_api_id: str,
    force_tools_first_round: bool,
    langsmith_slice: CompanionTurnLangsmithSlice,
    llm_round_timeout_sec: float,
    scope_registry_key: str,
    trace_id: str,
    user_msg_uuid: str,
    trace_hooks: ToolBackgroundTraceHooks | None,
) -> tuple[Any, _InitialToolBgCompletionMeta, list[dict[str, Any]]] | None:
    """First LLM round; ``None`` when aborted or timed out."""
    request_snapshot = deepcopy(working_messages)
    payload = _openai_messages_payload(working_messages)
    force_tools = bool(tools) and force_tools_first_round
    try:
        initial_response, initial_meta = await asyncio.wait_for(
            asyncio.to_thread(
                _initial_tool_bg_completion_with_fallbacks,
                resolved_client,
                chat_completion_sync,
                model=tool_api_id,
                messages_payload=payload,
                tools=tools,
                force_tools=force_tools,
                langsmith_slice=langsmith_slice,
            ),
            timeout=llm_round_timeout_sec,
        )
    except TimeoutError as exc:
        record_llm_inference_failure(
            model=tool_api_id,
            exc=exc,
            foreground_timeout_sec=llm_round_timeout_sec,
        )
        logger.warning(
            "repl.turn.bg initial round timed out trace_id={} user_msg_uuid={} "
            "timeout_sec={}",
            trace_id,
            user_msg_uuid,
            llm_round_timeout_sec,
        )
        return None

    if is_tool_background_aborted(user_msg_uuid):
        logger.debug(
            "repl.turn.bg aborted after initial api trace_id={} user_msg_uuid={}",
            trace_id,
            user_msg_uuid,
        )
        return None

    _log_bg_llm_round_result(
        round_idx=1,
        model=tool_api_id,
        resp=initial_response,
        request_messages=request_snapshot,
        scope_registry_key=scope_registry_key,
        trace_id=trace_id,
        trace_hooks=trace_hooks,
    )
    logger.debug(
        "repl.turn.bg initial_round_meta trace_id={} user_msg_uuid={} force_tools={} "
        "tool_choice={}",
        trace_id,
        user_msg_uuid,
        force_tools,
        initial_meta.tool_choice,
    )
    return initial_response, initial_meta, request_snapshot


def _log_tool_bg_no_tool_calls_early_exit(
    *,
    initial_response: Any,
    trace_id: str,
    user_msg_uuid: str,
) -> None:
    early_text = _assistant_text_from_completion_response(initial_response)
    finish0 = getattr(initial_response.choices[0], "finish_reason", None) or "?"
    if early_text.strip():
        logger.info(
            "repl.turn.bg no_tool_calls skip_output_queue trace_id={} "
            "user_msg_uuid={} chars={} finish_reason={} content_preview={} "
            "(foreground chat branch already shown)",
            trace_id,
            user_msg_uuid,
            len(early_text),
            finish0,
            _single_line_log_preview(early_text),
        )
    else:
        logger.debug(
            "repl.turn.bg no_tool_calls skip_transcript trace_id={} user_msg_uuid={} "
            "finish_reason={}",
            trace_id,
            user_msg_uuid,
            finish0,
        )


async def _tool_bg_continue_chat_round(
    *,
    messages_with_tool_results: list[dict[str, Any]],
    resolved_client: Any,
    chat_completion_sync: ChatCompletionsSyncPort,
    tool_api_id: str,
    tools: list[Any],
    langsmith_slice: CompanionTurnLangsmithSlice,
    llm_round_timeout_sec: float,
    scope_registry_key: str,
    trace_id: str,
    user_msg_uuid: str,
    trace_hooks: ToolBackgroundTraceHooks | None,
    progress: ToolBgLoopProgress,
) -> tuple[Any, str | None]:
    if is_tool_background_aborted(user_msg_uuid):
        raise BackgroundToolLoopAborted
    if progress.rounds_used >= _BG_TOOL_MAX_ROUNDS:
        raise ValueError(
            f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
        )
    progress.rounds_used += 1
    progress.active_round = progress.rounds_used
    request_snapshot_inner = deepcopy(messages_with_tool_results)
    inner_payload = _openai_messages_payload(messages_with_tool_results)
    try:
        next_resp = await asyncio.wait_for(
            asyncio.to_thread(
                chat_completion_sync,
                resolved_client,
                model=tool_api_id,
                messages_payload=inner_payload,
                tools=tools,
                langsmith_extra=langsmith_slice.tool_call_extra(
                    phase_suffix=SOURCE_TOOL_BACKGROUND_CONTINUE,
                    extra_metadata={
                        INTY_TOOL_BG_ROUND_METADATA_KEY: progress.active_round,
                    },
                ),
                high_reasoning=True,
            ),
            timeout=llm_round_timeout_sec,
        )
    except TimeoutError as exc:
        record_llm_inference_failure(
            model=tool_api_id,
            exc=exc,
            foreground_timeout_sec=llm_round_timeout_sec,
        )
        logger.warning(
            "repl.turn.bg continue round timed out trace_id={} "
            "user_msg_uuid={} round={} timeout_sec={}",
            trace_id,
            user_msg_uuid,
            progress.active_round,
            llm_round_timeout_sec,
        )
        raise BackgroundToolLoopAborted from exc
    _log_bg_llm_round_result(
        round_idx=progress.active_round,
        model=tool_api_id,
        resp=next_resp,
        request_messages=request_snapshot_inner,
        scope_registry_key=scope_registry_key,
        trace_id=trace_id,
        trace_hooks=trace_hooks,
    )
    tool_calls = getattr(next_resp.choices[0].message, "tool_calls", None) or []
    progress.total_tool_calls += len(tool_calls)
    return next_resp, None


def _tool_bg_after_tool_messages_appended(
    *,
    messages_with_tool_results: list[dict[str, Any]],
    memory_store: MemoryStore,
    companion_turn_track: CompanionTurnTrack,
    runtime_context: TurnRuntimeContext,
    tools: list[Any],
    turn_capture: ToolBgTurnCapture,
) -> list[Any]:
    turn_capture.appended_turn_msgs.extend(
        messages_with_tool_results[turn_capture.capture_from_len:]
    )
    turn_capture.capture_from_len = len(messages_with_tool_results)
    refreshed_tools = refresh_companion_turn_prompt_stack(
        store=memory_store,
        messages=messages_with_tool_results,
        track=companion_turn_track,
        runtime_context=runtime_context,
    )
    turn_capture.capture_from_len = len(messages_with_tool_results)
    return refreshed_tools


def _resolve_tool_bg_delivery_plan(
    *,
    loop_result: Any,
    appended_turn_msgs: list[dict[str, Any]],
    total_tool_calls: int,
    skip_finish_envelope_routing: bool,
    resolved_client: Any,
    tool_api_id: str,
    chat_completion_sync: ChatCompletionsSyncPort,
    trace_id: str,
    langsmith_slice: CompanionTurnLangsmithSlice,
    suppress_user_delivery: bool,
) -> ToolBgDeliveryPlan:
    raw_final = _assistant_text_from_completion_response(loop_result.response)
    bg_ls_trace = langsmith_trace_id_from_completion(loop_result.response)
    bg_ls_llm_run = langsmith_llm_run_id_from_completion(loop_result.response)
    tool_call_names = _extract_tool_call_names(appended_turn_msgs)
    image_paths = _local_paths_from_tool_messages(loop_result.messages)
    generation_deliver = _generation_tool_execution_deliver(
        appended_turn_msgs,
        tool_call_names,
        image_paths,
    )
    routing = resolve_tool_background_finish_envelope(
        skip_finish_envelope_routing=skip_finish_envelope_routing,
        client=resolved_client,
        model=tool_api_id,
        create_completion_sync=chat_completion_sync,
        conversation_messages=list(loop_result.messages),
        final_assistant_content=raw_final,
        trace_id=trace_id,
        langsmith_slice=langsmith_slice,
    )
    output_to_user_flag = routing.output_to_user
    should_push = tool_background_should_deliver_to_user(
        suppress_user_delivery=suppress_user_delivery,
        generation_deliver=generation_deliver,
        output_to_user=output_to_user_flag,
    )
    base_nl = (routing.user_facing_reply or "").strip()
    significance_meta = envelope_to_assistant_metadata_dict(routing)
    turn_recall = turn_recall_from_envelope(routing)
    if output_to_user_flag and not base_nl:
        filler = _tool_bg_nl_filler_from_appended_turn(appended_turn_msgs)
        if filler:
            base_nl = filler
    from app.core.companion_harness.tools.companion_user_feedback import (
        resolve_user_visible_feedback_display_text,
    )

    feedback_display = resolve_user_visible_feedback_display_text(
        llm_reply=base_nl,
        appended_turn_msgs=appended_turn_msgs,
    )
    deliver_output_to_user = output_to_user_flag
    if feedback_display is not None:
        display_text = feedback_display.display_text
        if display_text.strip():
            should_push = True
            deliver_output_to_user = True
    else:
        display_text = base_nl
    transcript_body = build_tool_background_transcript_body(
        display_text=display_text,
        appended_turn_msgs=appended_turn_msgs,
        total_tool_calls=total_tool_calls,
    )
    return ToolBgDeliveryPlan(
        should_push=should_push,
        deliver_output_to_user=deliver_output_to_user,
        display_text=display_text,
        transcript_body=transcript_body,
        significance_meta=significance_meta,
        turn_recall=turn_recall,
        output_to_user_flag=output_to_user_flag,
        generation_deliver=generation_deliver,
        tool_call_names=tool_call_names,
        image_paths=image_paths,
        bg_ls_trace=bg_ls_trace,
        bg_ls_llm_run=bg_ls_llm_run,
    )


def _persist_tool_bg_transcript_and_log(
    *,
    store: MemoryStore,
    user_msg_uuid: str,
    transcript_body: str,
    transcript_append_rel: str,
    trace_id: str,
    significance_meta: dict[str, Any] | None,
    turn_recall: str | None,
    elapsed_ms: int,
    rounds_used: int,
    total_tool_calls: int,
    image_paths: list[str],
) -> str:
    assistant_msg_uuid = str(uuid.uuid4())
    _append_background_transcript_assistant(
        store=store,
        content=transcript_body,
        assistant_msg_uuid=assistant_msg_uuid,
        reply_to=user_msg_uuid,
        trace_id=trace_id,
        transcript_relative_path=transcript_append_rel,
        significance_perception=significance_meta,
        turn_recall=turn_recall,
    )
    _append_background_log(
        store=store,
        user_msg_uuid=user_msg_uuid,
        assistant_msg_uuid=assistant_msg_uuid,
        elapsed_ms=elapsed_ms,
        rounds=rounds_used,
        tool_calls_count=total_tool_calls,
        generated_image_uris=image_paths,
        trace_id=trace_id,
    )
    return assistant_msg_uuid


@dataclass(frozen=True)
class _ToolBgLoopRunContext:
    """Immutable inputs shared across tool-bg loop phases."""

    memory_store: MemoryStore
    scope_registry_key: str
    transcript_append_rel: str
    image_asset_baseline: int
    tool_api_id: str
    trace_id: str
    user_msg_uuid: str
    resolved_client: Any
    chat_completion_sync: ChatCompletionsSyncPort
    tools: list[Any]
    langsmith_slice: CompanionTurnLangsmithSlice
    llm_round_timeout_sec: float
    trace_hooks: ToolBackgroundTraceHooks | None
    companion_turn_track: CompanionTurnTrack
    runtime_context: TurnRuntimeContext
    write_allowlist: frozenset[str] | None
    repository_only_store_text: bool
    skip_finish_envelope_routing: bool
    suppress_user_delivery: bool
    on_event: Callable[[ToolOutputEvent], None]
    activity_label: str | None
    execute_tool_call_fn: Callable[..., Any]


def _tool_bg_build_openai_loop_handlers(
    *,
    run_ctx: _ToolBgLoopRunContext,
    working_messages: list[dict[str, Any]],
    progress: ToolBgLoopProgress,
) -> _ToolBgOpenAiLoopHandlers:
    allow = (
        run_ctx.write_allowlist
        if run_ctx.write_allowlist is not None
        else MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST
    )
    turn_capture = ToolBgTurnCapture(
        appended_turn_msgs=[],
        capture_from_len=len(working_messages),
    )
    tools_for_rounds = list(run_ctx.tools)

    async def execute_tool_call(
        name: str, raw_arguments: str
    ) -> tuple[str, str | None]:
        result = await run_ctx.execute_tool_call_fn(
            run_ctx.memory_store,
            name,
            raw_arguments,
            write_allowlist=allow,
            repository_only_store_text=run_ctx.repository_only_store_text,
        )
        return result, None

    async def continue_chat(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[Any, str | None]:
        return await _tool_bg_continue_chat_round(
            messages_with_tool_results=messages_with_tool_results,
            resolved_client=run_ctx.resolved_client,
            chat_completion_sync=run_ctx.chat_completion_sync,
            tool_api_id=run_ctx.tool_api_id,
            tools=tools_for_rounds,
            langsmith_slice=run_ctx.langsmith_slice,
            llm_round_timeout_sec=run_ctx.llm_round_timeout_sec,
            scope_registry_key=run_ctx.scope_registry_key,
            trace_id=run_ctx.trace_id,
            user_msg_uuid=run_ctx.user_msg_uuid,
            trace_hooks=run_ctx.trace_hooks,
            progress=progress,
        )

    async def after_tool_messages_appended(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> None:
        nonlocal tools_for_rounds
        tools_for_rounds = _tool_bg_after_tool_messages_appended(
            messages_with_tool_results=messages_with_tool_results,
            memory_store=run_ctx.memory_store,
            companion_turn_track=run_ctx.companion_turn_track,
            runtime_context=run_ctx.runtime_context,
            tools=tools_for_rounds,
            turn_capture=turn_capture,
        )

    return _ToolBgOpenAiLoopHandlers(
        execute_tool_call=execute_tool_call,
        continue_chat=continue_chat,
        after_tool_messages_appended=after_tool_messages_appended,
        turn_capture=turn_capture,
        tools_for_rounds=tools_for_rounds,
    )


async def _tool_bg_invoke_openai_tool_call_loop(
    *,
    run_ctx: _ToolBgLoopRunContext,
    initial_response: Any,
    working_messages: list[dict[str, Any]],
    handlers: _ToolBgOpenAiLoopHandlers,
) -> Any | None:
    try:
        return await resolve_openai_tool_call_loop_async(
            response=initial_response,
            openai_messages=working_messages,
            max_tool_call_rounds=_BG_TOOL_MAX_ROUNDS,
            execute_tool_call=handlers.execute_tool_call,
            continue_chat=handlers.continue_chat,
            build_assistant_tool_call_message=openai_assistant_message_dict,
            insert_system_message=insert_openai_system_message,
            initial_trace_id=None,
            after_tool_messages_appended=handlers.after_tool_messages_appended,
        )
    except BackgroundToolLoopAborted:
        logger.debug(
            "repl.turn.bg aborted in tool loop trace_id={} user_msg_uuid={}",
            run_ctx.trace_id,
            run_ctx.user_msg_uuid,
        )
        return None
    except ValueError as exc:
        raise RuntimeError(
            f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
        ) from exc


async def _tool_bg_run_openai_tool_call_loop(
    *,
    run_ctx: _ToolBgLoopRunContext,
    initial_response: Any,
    working_messages: list[dict[str, Any]],
    progress: ToolBgLoopProgress,
) -> tuple[Any, ToolBgTurnCapture] | None:
    """Execute tool rounds; ``None`` when aborted or initial response has no tool calls."""
    initial_tool_calls = (
        getattr(initial_response.choices[0].message, "tool_calls", None) or []
    )
    if not initial_tool_calls:
        _log_tool_bg_no_tool_calls_early_exit(
            initial_response=initial_response,
            trace_id=run_ctx.trace_id,
            user_msg_uuid=run_ctx.user_msg_uuid,
        )
        return None
    progress.total_tool_calls += len(initial_tool_calls)

    handlers = _tool_bg_build_openai_loop_handlers(
        run_ctx=run_ctx,
        working_messages=working_messages,
        progress=progress,
    )
    loop_result = await _tool_bg_invoke_openai_tool_call_loop(
        run_ctx=run_ctx,
        initial_response=initial_response,
        working_messages=working_messages,
        handlers=handlers,
    )
    if loop_result is None:
        return None

    if is_tool_background_aborted(run_ctx.user_msg_uuid):
        logger.debug(
            "repl.turn.bg aborted before append trace_id={} user_msg_uuid={}",
            run_ctx.trace_id,
            run_ctx.user_msg_uuid,
        )
        return None
    return loop_result, handlers.turn_capture


def _tool_bg_log_delivery_policy_summary(
    *,
    run_ctx: _ToolBgLoopRunContext,
    plan: ToolBgDeliveryPlan,
) -> None:
    base_nl = (plan.display_text or "").strip()
    logger.debug(
        "repl.turn.bg policy_summary trace_id={} user_msg_uuid={} "
        "generation_deliver={} output_to_user={} should_push={} tools={} "
        "image_paths_n={} base_nl_chars={} display_chars={} transcript_body_chars={}",
        run_ctx.trace_id,
        run_ctx.user_msg_uuid,
        plan.generation_deliver,
        plan.output_to_user_flag,
        plan.deliver_output_to_user,
        plan.should_push,
        ",".join(plan.tool_call_names),
        len(plan.image_paths),
        len(base_nl),
        len(plan.display_text),
        len(plan.transcript_body),
    )


def _tool_bg_persist_when_should_not_push(
    *,
    run_ctx: _ToolBgLoopRunContext,
    plan: ToolBgDeliveryPlan,
    progress: ToolBgLoopProgress,
    elapsed_ms: int,
) -> None:
    if plan.transcript_body.strip():
        assistant_msg_uuid = _persist_tool_bg_transcript_and_log(
            store=run_ctx.memory_store,
            user_msg_uuid=run_ctx.user_msg_uuid,
            transcript_body=plan.transcript_body,
            transcript_append_rel=run_ctx.transcript_append_rel,
            trace_id=run_ctx.trace_id,
            significance_meta=plan.significance_meta,
            turn_recall=plan.turn_recall,
            elapsed_ms=elapsed_ms,
            rounds_used=progress.rounds_used,
            total_tool_calls=progress.total_tool_calls,
            image_paths=plan.image_paths,
        )
        logger.debug(
            "repl.turn.bg transcript_only trace_id={} user_msg_uuid={} "
            "assistant_msg_uuid={} reason=should_push_false",
            run_ctx.trace_id,
            run_ctx.user_msg_uuid,
            assistant_msg_uuid,
        )
    else:
        logger.debug(
            "repl.turn.bg suppress_user_visible_output trace_id={} user_msg_uuid={} "
            "reason=should_push_false_empty_transcript_body",
            run_ctx.trace_id,
            run_ctx.user_msg_uuid,
        )


def _tool_bg_persist_and_emit_user_delivery(
    *,
    run_ctx: _ToolBgLoopRunContext,
    plan: ToolBgDeliveryPlan,
    progress: ToolBgLoopProgress,
    elapsed_ms: int,
) -> None:
    assistant_msg_uuid = _persist_tool_bg_transcript_and_log(
        store=run_ctx.memory_store,
        user_msg_uuid=run_ctx.user_msg_uuid,
        transcript_body=plan.transcript_body,
        transcript_append_rel=run_ctx.transcript_append_rel,
        trace_id=run_ctx.trace_id,
        significance_meta=plan.significance_meta,
        turn_recall=plan.turn_recall,
        elapsed_ms=elapsed_ms,
        rounds_used=progress.rounds_used,
        total_tool_calls=progress.total_tool_calls,
        image_paths=plan.image_paths,
    )
    logger.debug(
        "repl.turn.bg deliver trace_id={} user_msg_uuid={} assistant_msg_uuid={} "
        "generation_deliver={} output_to_user={} nl_chars={} transcript_chars={} image_paths_n={}",
        run_ctx.trace_id,
        run_ctx.user_msg_uuid,
        assistant_msg_uuid,
        plan.generation_deliver,
        plan.output_to_user_flag,
        plan.deliver_output_to_user,
        len(plan.display_text.strip()),
        len(plan.transcript_body),
        len(plan.image_paths),
    )
    _emit_tool_bg_delivery_event(
        on_event=run_ctx.on_event,
        scope_registry_key=run_ctx.scope_registry_key,
        memory_store=run_ctx.memory_store,
        user_msg_uuid=run_ctx.user_msg_uuid,
        assistant_msg_uuid=assistant_msg_uuid,
        plan=plan,
        elapsed_ms=elapsed_ms,
        trace_id=run_ctx.trace_id,
        image_asset_baseline=run_ctx.image_asset_baseline,
        activity_label=run_ctx.activity_label,
    )


def _tool_bg_apply_delivery_plan(
    *,
    run_ctx: _ToolBgLoopRunContext,
    loop_result: Any,
    turn_capture: ToolBgTurnCapture,
    progress: ToolBgLoopProgress,
    t0: float,
) -> None:
    """Persist transcript rows and emit user-visible tool-bg output when applicable."""
    plan = _resolve_tool_bg_delivery_plan(
        loop_result=loop_result,
        appended_turn_msgs=turn_capture.appended_turn_msgs,
        total_tool_calls=progress.total_tool_calls,
        skip_finish_envelope_routing=run_ctx.skip_finish_envelope_routing,
        resolved_client=run_ctx.resolved_client,
        tool_api_id=run_ctx.tool_api_id,
        chat_completion_sync=run_ctx.chat_completion_sync,
        trace_id=run_ctx.trace_id,
        langsmith_slice=run_ctx.langsmith_slice,
        suppress_user_delivery=run_ctx.suppress_user_delivery,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000.0)
    _tool_bg_log_delivery_policy_summary(run_ctx=run_ctx, plan=plan)

    if is_tool_background_aborted(run_ctx.user_msg_uuid):
        logger.debug(
            "repl.turn.bg aborted before transcript append trace_id={} user_msg_uuid={}",
            run_ctx.trace_id,
            run_ctx.user_msg_uuid,
        )
        return

    if not plan.should_push:
        _tool_bg_persist_when_should_not_push(
            run_ctx=run_ctx,
            plan=plan,
            progress=progress,
            elapsed_ms=elapsed_ms,
        )
        return

    if not plan.transcript_body.strip() and not plan.generation_deliver:
        logger.debug(
            "repl.turn.bg suppress_user_visible_output empty_transcript trace_id={} "
            "user_msg_uuid={} generation_deliver={} output_to_user={} tools={}",
            run_ctx.trace_id,
            run_ctx.user_msg_uuid,
            plan.generation_deliver,
            plan.output_to_user_flag,
            ",".join(plan.tool_call_names),
        )
        return

    _tool_bg_persist_and_emit_user_delivery(
        run_ctx=run_ctx,
        plan=plan,
        progress=progress,
        elapsed_ms=elapsed_ms,
    )


def _emit_tool_bg_delivery_event(
    *,
    on_event: Callable[[ToolOutputEvent], None],
    scope_registry_key: str,
    memory_store: MemoryStore,
    user_msg_uuid: str,
    assistant_msg_uuid: str,
    plan: ToolBgDeliveryPlan,
    elapsed_ms: int,
    trace_id: str,
    image_asset_baseline: int,
    activity_label: str | None,
) -> None:
    on_event(
        ToolOutputEvent(
            scope_registry_key=scope_registry_key,
            memory_store=memory_store,
            user_msg_uuid=user_msg_uuid,
            assistant_msg_uuid=assistant_msg_uuid,
            text=plan.display_text,
            ts=utc_iso_ts(),
            elapsed_ms=elapsed_ms,
            trace_id=trace_id,
            langsmith_trace_id=plan.bg_ls_trace,
            langsmith_run_id=plan.bg_ls_llm_run,
            output_to_user=plan.deliver_output_to_user,
            generation_deliver=plan.generation_deliver,
            image_asset_baseline=image_asset_baseline,
            local_image_paths=tuple(plan.image_paths),
            significance_perception=plan.significance_meta,
            turn_recall=plan.turn_recall,
            inner_tick_activity=activity_label,
        )
    )


def _tool_bg_new_loop_run_context(
    *,
    memory_store: MemoryStore,
    scope_registry_key: str,
    transcript_append_rel: str,
    image_asset_baseline: int,
    tool_api_id: str,
    trace_id: str,
    user_msg_uuid: str,
    resolved_client: Any,
    chat_completion_sync: ChatCompletionsSyncPort,
    tools: list[Any],
    langsmith_slice: CompanionTurnLangsmithSlice,
    llm_round_timeout_sec: float,
    trace_hooks: ToolBackgroundTraceHooks | None,
    companion_turn_track: CompanionTurnTrack,
    runtime_context: TurnRuntimeContext,
    write_allowlist: frozenset[str] | None,
    repository_only_store_text: bool,
    skip_finish_envelope_routing: bool,
    suppress_user_delivery: bool,
    on_event: Callable[[ToolOutputEvent], None],
    activity_label: str | None,
    execute_tool_call_fn: Callable[..., Any],
) -> _ToolBgLoopRunContext:
    return _ToolBgLoopRunContext(
        memory_store=memory_store,
        scope_registry_key=scope_registry_key,
        transcript_append_rel=transcript_append_rel,
        image_asset_baseline=image_asset_baseline,
        tool_api_id=tool_api_id,
        trace_id=trace_id,
        user_msg_uuid=user_msg_uuid,
        resolved_client=resolved_client,
        chat_completion_sync=chat_completion_sync,
        tools=tools,
        langsmith_slice=langsmith_slice,
        llm_round_timeout_sec=llm_round_timeout_sec,
        trace_hooks=trace_hooks,
        companion_turn_track=companion_turn_track,
        runtime_context=runtime_context,
        write_allowlist=write_allowlist,
        repository_only_store_text=repository_only_store_text,
        skip_finish_envelope_routing=skip_finish_envelope_routing,
        suppress_user_delivery=suppress_user_delivery,
        on_event=on_event,
        activity_label=activity_label,
        execute_tool_call_fn=execute_tool_call_fn,
    )


async def _tool_bg_run_loop_through_delivery(
    *,
    run_ctx: _ToolBgLoopRunContext,
    initial_response: Any,
    working_messages: list[dict[str, Any]],
    progress: ToolBgLoopProgress,
    t0: float,
) -> None:
    loop_phase = await _tool_bg_run_openai_tool_call_loop(
        run_ctx=run_ctx,
        initial_response=initial_response,
        working_messages=working_messages,
        progress=progress,
    )
    if loop_phase is None:
        return
    loop_result, turn_capture = loop_phase
    _tool_bg_apply_delivery_plan(
        run_ctx=run_ctx,
        loop_result=loop_result,
        turn_capture=turn_capture,
        progress=progress,
        t0=t0,
    )


async def run_tool_background_loop(
    *,
    memory_store: MemoryStore,
    request_messages: list[dict[str, Any]],
    tool_model: GenAIModel,
    user_msg_uuid: str,
    trace_id: str,
    tools: list[Any],
    on_event: Callable[[ToolOutputEvent], None],
    execute_tool_call_fn: Callable[..., Any],
    client: Any,
    chat_completion_sync: ChatCompletionsSyncPort,
    companion_turn_track: CompanionTurnTrack,
    llm_round_timeout_sec: float,
    trace_hooks: ToolBackgroundTraceHooks | None = None,
    write_allowlist: frozenset[str] | None = None,
    repository_only_store_text: bool = False,
    suppress_user_delivery: bool = False,
    skip_finish_envelope_routing: bool = False,
    activity_label: str | None = None,
    # TODO(#3411): tool_background passes implicit_signal_bundle=None — LangSmith tool_* spans
    # omit ``## User's Local Time Context``; verify injection on foreground agentic_companion_chat only.
    runtime_context: TurnRuntimeContext = TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    ),
    langsmith_slice: CompanionTurnLangsmithSlice,
    force_tools_first_round: bool = True,
) -> None:
    assert llm_round_timeout_sec > 0.0
    scope_registry_key = memory_store.scope.registry_key()
    image_asset_baseline = len(list_image_asset_records(memory_store))
    transcript_append_rel = transcript_relative_path_for_turn_persistence(
        track=companion_turn_track,
    )
    tool_api_id = tool_model.id_on_provider
    try:
        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg skip aborted before start trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return

        resolved_client = client
        t0 = time.perf_counter()
        working_messages = deepcopy(request_messages)
        progress = ToolBgLoopProgress(
            rounds_used=0,
            active_round=0,
            total_tool_calls=0,
        )

        initial_fetch = await _fetch_tool_bg_initial_completion(
            resolved_client=resolved_client,
            chat_completion_sync=chat_completion_sync,
            working_messages=working_messages,
            tools=tools,
            tool_api_id=tool_api_id,
            force_tools_first_round=force_tools_first_round,
            langsmith_slice=langsmith_slice,
            llm_round_timeout_sec=llm_round_timeout_sec,
            scope_registry_key=scope_registry_key,
            trace_id=trace_id,
            user_msg_uuid=user_msg_uuid,
            trace_hooks=trace_hooks,
        )
        if initial_fetch is None:
            return
        initial_response, _initial_meta, _request_snapshot = initial_fetch

        progress.rounds_used = 1
        progress.active_round = progress.rounds_used
        run_ctx = _tool_bg_new_loop_run_context(
            memory_store=memory_store,
            scope_registry_key=scope_registry_key,
            transcript_append_rel=transcript_append_rel,
            image_asset_baseline=image_asset_baseline,
            tool_api_id=tool_api_id,
            trace_id=trace_id,
            user_msg_uuid=user_msg_uuid,
            resolved_client=resolved_client,
            chat_completion_sync=chat_completion_sync,
            tools=tools,
            langsmith_slice=langsmith_slice,
            llm_round_timeout_sec=llm_round_timeout_sec,
            trace_hooks=trace_hooks,
            companion_turn_track=companion_turn_track,
            runtime_context=runtime_context,
            write_allowlist=write_allowlist,
            repository_only_store_text=repository_only_store_text,
            skip_finish_envelope_routing=skip_finish_envelope_routing,
            suppress_user_delivery=suppress_user_delivery,
            on_event=on_event,
            activity_label=activity_label,
            execute_tool_call_fn=execute_tool_call_fn,
        )
        await _tool_bg_run_loop_through_delivery(
            run_ctx=run_ctx,
            initial_response=initial_response,
            working_messages=working_messages,
            progress=progress,
            t0=t0,
        )
    finally:
        clear_tool_background_abort_flag(user_msg_uuid)
