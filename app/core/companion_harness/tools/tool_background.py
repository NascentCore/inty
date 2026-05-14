"""Background tool execution queue for async dual-LLM mode.

Persists tool return strings under a ``--- Tool results ---`` section on ``source=tool_bg``
transcript rows so the following ``run_turn`` sees them in chat/tool message assembly.
Optional ``tool_bg_idle_event`` coordinates per-session ordering with ``turn.run_turn``.
"""

from __future__ import annotations

import asyncio
import queue
import re
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from loguru import logger
from openai import BadRequestError

from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agent_status_line import (
    clear_tool_background_db_loop,
    set_tool_background_db_loop,
)
from app.utils.config import CompanionMemoryBootstrapType

from app.core.companion_harness.llm.chat_completions import create_chat_completion_sync
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    INTY_TOOL_BG_ROUND_METADATA_KEY,
    SOURCE_TOOL_BACKGROUND_CONTINUE,
    SOURCE_TOOL_BACKGROUND_INITIAL,
    tool_call_langsmith_extra,
    tool_choice_attempt_metadata,
)
from app.core.companion_harness.llm.ports import ChatCompletionsSyncPort
from app.core.companion_harness.tools.runtime import (
    resolve_official_assistant_tool_loop_async,
)

from app.core.companion_harness.companion.llm_chat_runtime import (
    companion_turn_langsmith_parent_trace_id_str,
    end_companion_turn_root_run_safe,
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
    tool_path_chat_completion_kwargs,
)
from app.core.companion_harness.companion.llm_client import (
    LLM_SCENE_TOOL_CALL,
    CompanionLLMClient,
)
from app.core.companion_harness.companion.llm_runtime_events import (
    LlmRuntimeEventBind,
    companion_llm_runtime_event_bind_ctx,
    exc_chain_includes_llm_inference_failure_root_causes,
)
from app.core.companion_harness.companion.creative_dream_fragment import (
    maybe_append_creative_dream_fragment_after_consolidation,
)
from app.core.companion_harness.companion.dream_state import record_companion_dream_cycle_completed
from app.core.companion_harness.companion.models import InnerTickMode, transcript_relative_path_for_turn_persistence
from app.core.companion_harness.companion.prompt_stack import refresh_companion_turn_prompt_stack
from app.core.companion_harness.companion.runtime_events import append_runtime_event
from app.core.companion_harness.companion.significance_perception import envelope_to_assistant_metadata_dict
from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.memory.memory_store import MemoryStore

from .companion_tool_runtime import (
    REPL_WRITABLE_RELATIVE_PATHS,
    execute_tool_call,
    openai_assistant_message_dict,
    round_includes_generation_tool,
    tool_requires_client_delivery_on_success,
)
from .image_gate import list_image_asset_records
from .runtime_inspect_context import (
    build_last_chat_completion_request_payload,
    runtime_inspect_set_last_chat_completion_request,
    runtime_inspect_thread_overlay_begin,
    runtime_inspect_thread_overlay_end,
    tools_summary_from_openai_tools,
)
from .tool_bg_routing import resolve_tool_bg_routing_sync

_OUTPUT_QUEUE: queue.Queue["ToolOutputEvent"] | None = None
_OUTPUT_QUEUE_LOCK = threading.Lock()
_ACTIVE_THREADS: set[threading.Thread] = set()
_ACTIVE_THREADS_LOCK = threading.Lock()
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


def mark_tool_background_aborted(user_msg_uuid: str) -> None:
    """Foreground REPL superseded this turn: background job must not append transcript or events."""
    with _ABORT_TOOL_BG_LOCK:
        _ABORTED_TOOL_BG_USER_MSG_UUIDS.add(user_msg_uuid)


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
        digest_core = _tool_bg_nl_filler_from_appended_turn(appended_turn_msgs).strip()
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


def _insert_system_message(
    openai_messages: list[dict[str, Any]],
    system_message_content: str,
) -> None:
    insertion_index = 0
    while (
        insertion_index < len(openai_messages)
        and openai_messages[insertion_index].get("role") == "system"
    ):
        insertion_index += 1
    openai_messages.insert(
        insertion_index, {"role": "system", "content": system_message_content}
    )


@dataclass(frozen=True)
class ToolOutputEvent:
    scope_registry_key: str
    memory_store: MemoryStore
    user_msg_uuid: str
    assistant_msg_uuid: str
    text: str
    ts: str
    elapsed_ms: int
    trace_id: str = ""  # run_turn turn id; links transcript rows + tool_background_done
    langsmith_trace_id: str = ""
    langsmith_run_id: str = ""
    output_to_user: bool = False
    generation_deliver: bool = False
    # Same dual-LLM envelope fields as foreground CompanionTurnResult (routing layer runs TTS).
    reply_modality: str = "text"
    voice_message_script: str = ""
    image_asset_baseline: int = 0
    # Absolute on-disk paths for images created during this background tool round.
    # Surfaced to REPL via meta_data.tool_bg_local_image_paths; production clients ignore.
    local_image_paths: tuple[str, ...] = ()
    # Parsed from unified finish envelope; mirrors foreground significance_perception shape.
    significance_perception: dict[str, Any] | None = None
    # InnerTickMode.value when this background round is an inner-tick turn; else None.
    inner_tick_activity: str | None = None


def output_queue() -> queue.Queue[ToolOutputEvent]:
    global _OUTPUT_QUEUE
    with _OUTPUT_QUEUE_LOCK:
        if _OUTPUT_QUEUE is None:
            _OUTPUT_QUEUE = queue.Queue()
        return _OUTPUT_QUEUE


def clear_output_queue() -> None:
    q = output_queue()
    while True:
        try:
            q.get_nowait()
        except queue.Empty:
            return


def push_output_event(event: ToolOutputEvent) -> None:
    output_queue().put(event)


def pop_output_events_nowait(*, scope_registry_key: str) -> list[ToolOutputEvent]:
    want = scope_registry_key.strip()
    out: list[ToolOutputEvent] = []
    q = output_queue()
    parked: list[ToolOutputEvent] = []
    while True:
        try:
            ev = q.get_nowait()
        except queue.Empty:
            break
        if ev.scope_registry_key == want:
            out.append(ev)
        else:
            parked.append(ev)
    for ev in parked:
        q.put(ev)
    return out


def _register_thread(worker: threading.Thread) -> None:
    with _ACTIVE_THREADS_LOCK:
        _ACTIVE_THREADS.add(worker)


def _unregister_thread(worker: threading.Thread) -> None:
    with _ACTIVE_THREADS_LOCK:
        _ACTIVE_THREADS.discard(worker)


def background_tasks_count() -> int:
    with _ACTIVE_THREADS_LOCK:
        return len(_ACTIVE_THREADS)


def _assistant_text_from_completion_response(resp: Any) -> str:
    # TODO(companion-dual-envelope-reasoning-channel): Tool-background path only reads ``.content``;
    # same provider quirk as foreground ``turn.py`` when switching reasoning-heavy chat models.
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
    """Winning attempt parameters for tool_background first completion (runtime_inspect)."""

    tool_choice: str | None


def _initial_tool_bg_completion_with_fallbacks(
    client: Any,
    chat_completion_sync: ChatCompletionsSyncPort,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
    force_tools: bool,
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
                langsmith_extra=tool_call_langsmith_extra(
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


def _openai_messages_payload(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]


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
) -> None:
    store.append_jsonl_record(
        transcript_relative_path,
        {
            "role": "assistant",
            "content": content,
            "ts": utc_iso_ts(),
            "uuid": assistant_msg_uuid,
            "source": "tool_bg",
            "reply_to": reply_to,
            "trace_id": trace_id,
        },
    )


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
        "tool_background.jsonl",
        row,
    )


def _finalize_dream_inner_tick_success(
    memory_store: MemoryStore,
    *,
    implicit_signal_bundle: ImplicitSignalBundle | None,
    companion_llm_client_for_aux: CompanionLLMClient | None,
) -> None:
    feats = global_config_loaded_from_config_yaml.app.features
    qh = float(feats.companion_ws_inner_tick_quiet_hours_after_dream)
    record_companion_dream_cycle_completed(
        memory_store,
        inner_tick_quiet_hours=qh if qh > 0 else None,
    )
    if companion_llm_client_for_aux is None:
        return
    if feats.companion_creative_dream_probability <= 0.0:
        return
    maybe_append_creative_dream_fragment_after_consolidation(
        store=memory_store,
        llm_client=companion_llm_client_for_aux,
        feats=feats,
        implicit=implicit_signal_bundle,
    )


async def _run_background_tool_loop(
    *,
    memory_store: MemoryStore,
    request_messages: list[dict[str, Any]],
    tool_model_name: str,
    user_msg_uuid: str,
    trace_id: str,
    tools: list[Any],
    on_event: Callable[[ToolOutputEvent], None],
    execute_tool_call_fn: Callable[..., Any],
    client: Any,
    chat_completion_sync: ChatCompletionsSyncPort,
    trace_hooks: ToolBackgroundTraceHooks | None = None,
    write_allowlist: frozenset[str] | None = None,
    repository_only_store_text: bool = False,
    memory_bootstrap_type: str = CompanionMemoryBootstrapType.NONE.value,
    inner_tick_turn: bool = False,
    inner_tick_mode: InnerTickMode = InnerTickMode.MAINTENANCE,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    force_tools_first_round: bool = True,
    companion_llm_client_for_aux: CompanionLLMClient | None = None,
) -> None:
    scope_registry_key = memory_store.scope.registry_key()
    image_asset_baseline = len(list_image_asset_records(memory_store))
    transcript_append_rel = transcript_relative_path_for_turn_persistence(
        inner_tick_turn=inner_tick_turn,
        inner_tick_mode=inner_tick_mode,
    )
    try:
        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg skip aborted before start trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return

        runtime_inspect_thread_overlay_begin(
            {
                "runtime_config": {
                    "source": "tool_background",
                    "tool_model_name": tool_model_name,
                    "trace_id": trace_id,
                    "inner_tick_turn": inner_tick_turn,
                    "inner_tick_mode": inner_tick_mode.value,
                    "tools_summary": tools_summary_from_openai_tools(tools),
                    "force_tools_first_round": force_tools_first_round,
                    "llm_call_notes": (
                        "Foreground CompanionLLMConfig is not copied into this async tool_background "
                        "path; use tool_model_name and last_chat_completion_request. "
                        "temperature/max_tokens are not set in companion code (provider defaults)."
                    ),
                    "openrouter_extra_body_tool_path": tool_path_chat_completion_kwargs(
                        tool_model_name
                    ),
                },
                "last_chat_completion_request": None,
                "scoped_memory_store": memory_store,
                "correlation": {
                    "trace_id": trace_id,
                    "user_msg_uuid": user_msg_uuid,
                },
            }
        )

        resolved_client = client
        t0 = time.perf_counter()
        working_messages = deepcopy(request_messages)
        total_tool_calls = 0
        rounds_used = 0
        active_round = 0

        request_snapshot = deepcopy(working_messages)
        payload = _openai_messages_payload(working_messages)
        force_tools = bool(tools) and force_tools_first_round
        initial_response, initial_meta = await asyncio.to_thread(
            _initial_tool_bg_completion_with_fallbacks,
            resolved_client,
            chat_completion_sync,
            model=tool_model_name,
            messages_payload=payload,
            tools=tools,
            force_tools=force_tools,
        )
        runtime_inspect_set_last_chat_completion_request(
            build_last_chat_completion_request_payload(
                model=tool_model_name,
                messages=list(payload),
                tools=tools,
                tool_choice=initial_meta.tool_choice,
                response_format_json_schema_name=None,
            )
        )

        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg aborted after initial api trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return

        rounds_used += 1
        active_round = rounds_used
        _log_bg_llm_round_result(
            round_idx=active_round,
            model=tool_model_name,
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

        initial_tool_calls = (
            getattr(initial_response.choices[0].message, "tool_calls", None) or []
        )
        if not initial_tool_calls:
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
            return
        total_tool_calls += len(initial_tool_calls)

        allow = (
            write_allowlist
            if write_allowlist is not None
            else REPL_WRITABLE_RELATIVE_PATHS
        )

        async def execute_tool_call(
            name: str, raw_arguments: str
        ) -> tuple[str, str | None]:
            result = await execute_tool_call_fn(
                memory_store,
                name,
                raw_arguments,
                write_allowlist=allow,
                repository_only_store_text=repository_only_store_text,
            )
            return result, None

        async def continue_chat(
            messages_with_tool_results: list[dict[str, Any]],
        ) -> tuple[Any, str | None]:
            nonlocal rounds_used, active_round, total_tool_calls
            if is_tool_background_aborted(user_msg_uuid):
                raise BackgroundToolLoopAborted
            if rounds_used >= _BG_TOOL_MAX_ROUNDS:
                raise ValueError(
                    f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
                )
            rounds_used += 1
            active_round = rounds_used
            request_snapshot_inner = deepcopy(messages_with_tool_results)
            inner_payload = _openai_messages_payload(messages_with_tool_results)
            runtime_inspect_set_last_chat_completion_request(
                build_last_chat_completion_request_payload(
                    model=tool_model_name,
                    messages=list(inner_payload),
                    tools=tools,
                )
            )
            next_resp = await asyncio.to_thread(
                chat_completion_sync,
                resolved_client,
                model=tool_model_name,
                messages_payload=inner_payload,
                tools=tools,
                langsmith_extra=tool_call_langsmith_extra(
                    phase_suffix=SOURCE_TOOL_BACKGROUND_CONTINUE,
                    extra_metadata={
                        INTY_TOOL_BG_ROUND_METADATA_KEY: active_round,
                    },
                ),
                high_reasoning=True,
            )
            _log_bg_llm_round_result(
                round_idx=active_round,
                model=tool_model_name,
                resp=next_resp,
                request_messages=request_snapshot_inner,
                scope_registry_key=scope_registry_key,
                trace_id=trace_id,
                trace_hooks=trace_hooks,
            )
            tool_calls = getattr(next_resp.choices[0].message, "tool_calls", None) or []
            total_tool_calls += len(tool_calls)
            return next_resp, None

        # Keep tool-path system prefix and OpenAI tools list in sync with MemoryStore scope
        # after each tool round (same idea as sync loop in turn.py after tool replies).
        async def _after_tool_messages_appended(
            messages_with_tool_results: list[dict[str, Any]],
        ) -> None:
            nonlocal tools
            tools = refresh_companion_turn_prompt_stack(
                store=memory_store,
                memory_bootstrap_type=memory_bootstrap_type,
                inner_tick_turn=inner_tick_turn,
                inner_tick_mode=inner_tick_mode,
                messages=messages_with_tool_results,
                tool_side_compact_system_prompt=True,
                implicit_signal_bundle=implicit_signal_bundle,
            )

        try:
            loop_result = await resolve_official_assistant_tool_loop_async(
                response=initial_response,
                openai_messages=working_messages,
                max_tool_call_rounds=_BG_TOOL_MAX_ROUNDS,
                execute_tool_call=execute_tool_call,
                continue_chat=continue_chat,
                build_assistant_tool_call_message=openai_assistant_message_dict,
                insert_system_message=_insert_system_message,
                initial_trace_id=None,
                after_tool_messages_appended=_after_tool_messages_appended,
            )
        except BackgroundToolLoopAborted:
            logger.debug(
                "repl.turn.bg aborted in tool loop trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return
        except ValueError as exc:
            raise RuntimeError(
                f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
            ) from exc

        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg aborted before append trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return

        raw_final = _assistant_text_from_completion_response(loop_result.response)
        bg_ls_trace = langsmith_trace_id_from_completion(loop_result.response)
        bg_ls_llm_run = langsmith_llm_run_id_from_completion(loop_result.response)
        appended_turn_msgs = loop_result.messages[len(working_messages) :]
        tool_call_names = _extract_tool_call_names(appended_turn_msgs)
        image_paths = _local_paths_from_tool_messages(loop_result.messages)
        generation_deliver = _generation_tool_execution_deliver(
            appended_turn_msgs, tool_call_names, image_paths
        )
        routing = resolve_tool_bg_routing_sync(
            client=resolved_client,
            model=tool_model_name,
            create_completion_sync=chat_completion_sync,
            conversation_messages=list(loop_result.messages),
            final_assistant_content=raw_final,
            trace_id=trace_id,
        )
        output_to_user_flag = routing.output_to_user
        should_push = generation_deliver or output_to_user_flag
        base_nl = (routing.user_facing_reply or "").strip()
        significance_meta = envelope_to_assistant_metadata_dict(routing)
        if output_to_user_flag and not base_nl:
            filler = _tool_bg_nl_filler_from_appended_turn(appended_turn_msgs)
            if filler:
                base_nl = filler
        # Local image paths now travel out-of-band on ToolOutputEvent.local_image_paths
        # (REPL surfaces them as a banner). Body text stays NL-only for production clients.
        display_text = base_nl
        elapsed_ms = int((time.perf_counter() - t0) * 1000.0)

        transcript_body = build_tool_background_transcript_body(
            display_text=display_text,
            appended_turn_msgs=appended_turn_msgs,
            total_tool_calls=total_tool_calls,
        )

        logger.debug(
            "repl.turn.bg policy_summary trace_id={} user_msg_uuid={} "
            "generation_deliver={} output_to_user={} should_push={} tools={} "
            "image_paths_n={} base_nl_chars={} display_chars={} transcript_body_chars={}",
            trace_id,
            user_msg_uuid,
            generation_deliver,
            output_to_user_flag,
            should_push,
            ",".join(tool_call_names),
            len(image_paths),
            len(base_nl),
            len(display_text),
            len(transcript_body),
        )

        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg aborted before transcript append trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return

        if not should_push:
            if transcript_body.strip():
                assistant_msg_uuid = str(uuid.uuid4())
                _append_background_transcript_assistant(
                    store=memory_store,
                    content=transcript_body,
                    assistant_msg_uuid=assistant_msg_uuid,
                    reply_to=user_msg_uuid,
                    trace_id=trace_id,
                    transcript_relative_path=transcript_append_rel,
                )
                _append_background_log(
                    store=memory_store,
                    user_msg_uuid=user_msg_uuid,
                    assistant_msg_uuid=assistant_msg_uuid,
                    elapsed_ms=elapsed_ms,
                    rounds=rounds_used,
                    tool_calls_count=total_tool_calls,
                    generated_image_uris=image_paths,
                    trace_id=trace_id,
                )
                if inner_tick_turn and inner_tick_mode == InnerTickMode.DREAM:
                    _finalize_dream_inner_tick_success(
                        memory_store,
                        implicit_signal_bundle=implicit_signal_bundle,
                        companion_llm_client_for_aux=companion_llm_client_for_aux,
                    )
                logger.debug(
                    "repl.turn.bg transcript_only trace_id={} user_msg_uuid={} "
                    "assistant_msg_uuid={} reason=should_push_false",
                    trace_id,
                    user_msg_uuid,
                    assistant_msg_uuid,
                )
            else:
                logger.debug(
                    "repl.turn.bg suppress_user_visible_output trace_id={} user_msg_uuid={} "
                    "reason=should_push_false_empty_transcript_body",
                    trace_id,
                    user_msg_uuid,
                )
            return

        if not transcript_body.strip() and not generation_deliver:
            logger.debug(
                "repl.turn.bg suppress_user_visible_output empty_transcript trace_id={} "
                "user_msg_uuid={} generation_deliver={} output_to_user={} tools={}",
                trace_id,
                user_msg_uuid,
                generation_deliver,
                output_to_user_flag,
                ",".join(tool_call_names),
            )
            return
        assistant_msg_uuid = str(uuid.uuid4())
        _append_background_transcript_assistant(
            store=memory_store,
            content=transcript_body,
            assistant_msg_uuid=assistant_msg_uuid,
            reply_to=user_msg_uuid,
            trace_id=trace_id,
            transcript_relative_path=transcript_append_rel,
        )
        _append_background_log(
            store=memory_store,
            user_msg_uuid=user_msg_uuid,
            assistant_msg_uuid=assistant_msg_uuid,
            elapsed_ms=elapsed_ms,
            rounds=rounds_used,
            tool_calls_count=total_tool_calls,
            generated_image_uris=image_paths,
            trace_id=trace_id,
        )
        if inner_tick_turn and inner_tick_mode == InnerTickMode.DREAM:
            _finalize_dream_inner_tick_success(
                memory_store,
                implicit_signal_bundle=implicit_signal_bundle,
                companion_llm_client_for_aux=companion_llm_client_for_aux,
            )
        logger.debug(
            "repl.turn.bg deliver trace_id={} user_msg_uuid={} assistant_msg_uuid={} "
            "generation_deliver={} output_to_user={} nl_chars={} transcript_chars={} image_paths_n={}",
            trace_id,
            user_msg_uuid,
            assistant_msg_uuid,
            generation_deliver,
            output_to_user_flag,
            len(display_text.strip()),
            len(transcript_body),
            len(image_paths),
        )
        on_event(
            ToolOutputEvent(
                scope_registry_key=scope_registry_key,
                memory_store=memory_store,
                user_msg_uuid=user_msg_uuid,
                assistant_msg_uuid=assistant_msg_uuid,
                text=display_text,
                ts=utc_iso_ts(),
                elapsed_ms=elapsed_ms,
                trace_id=trace_id,
                langsmith_trace_id=bg_ls_trace,
                langsmith_run_id=bg_ls_llm_run,
                output_to_user=output_to_user_flag,
                generation_deliver=generation_deliver,
                reply_modality=routing.reply_modality,
                voice_message_script=(routing.voice_message_script or "").strip(),
                image_asset_baseline=image_asset_baseline,
                local_image_paths=tuple(image_paths),
                significance_perception=significance_meta,
                inner_tick_activity=(
                    inner_tick_mode.value if inner_tick_turn else None
                ),
            )
        )
    finally:
        runtime_inspect_thread_overlay_end()
        clear_tool_background_abort_flag(user_msg_uuid)


def start_tool_background_job(
    *,
    memory_store: MemoryStore,
    request_messages: list[dict[str, Any]],
    tool_model_name: str,
    user_msg_uuid: str,
    trace_id: str,
    tools: list[Any],
    on_event: Callable[[ToolOutputEvent], None] | None = None,
    execute_tool_call_fn: Callable[..., Any] = execute_tool_call,
    client: Any,
    chat_completions_sync: ChatCompletionsSyncPort | None = None,
    trace_hooks: ToolBackgroundTraceHooks | None = None,
    write_allowlist: frozenset[str] | None = None,
    repository_only_store_text: bool = False,
    main_event_loop: asyncio.AbstractEventLoop | None = None,
    langsmith_parent_run: Any | None = None,
    memory_bootstrap_type: str = CompanionMemoryBootstrapType.NONE.value,
    inner_tick_turn: bool = False,
    inner_tick_mode: InnerTickMode = InnerTickMode.MAINTENANCE,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    tool_bg_idle_event: threading.Event | None = None,
    force_tools_first_round: bool = True,
    companion_llm_client_for_aux: CompanionLLMClient | None = None,
) -> None:
    sync_port = chat_completions_sync or create_chat_completion_sync

    def _effective_on_event(ev: ToolOutputEvent) -> None:
        if on_event is not None:
            on_event(ev)
        else:
            push_output_event(ev)

    def _runner() -> None:
        # Register here with current_thread(), not the Thread instance from threading.Thread(...).
        # Unit tests patch threading.Thread with MagicMock; pre-start register would leak mocks.
        _register_thread(threading.current_thread())
        _tb_phase = "inner_tick" if inner_tick_turn else "tool_background"
        llm_bg_bind_token = companion_llm_runtime_event_bind_ctx.set(
            LlmRuntimeEventBind(
                memory_store=memory_store,
                trace_id=trace_id,
                user_msg_uuid=user_msg_uuid,
                phase=_tb_phase,
                scene=LLM_SCENE_TOOL_CALL,
            )
        )
        bg_ls_err: str | None = None

        def _run_async_tool_loop() -> None:
            asyncio.run(
                _run_background_tool_loop(
                    memory_store=memory_store,
                    request_messages=request_messages,
                    tool_model_name=tool_model_name,
                    user_msg_uuid=user_msg_uuid,
                    trace_id=trace_id,
                    tools=tools,
                    on_event=_effective_on_event,
                    execute_tool_call_fn=execute_tool_call_fn,
                    client=client,
                    chat_completion_sync=sync_port,
                    trace_hooks=trace_hooks,
                    write_allowlist=write_allowlist,
                    repository_only_store_text=repository_only_store_text,
                    memory_bootstrap_type=memory_bootstrap_type,
                    inner_tick_turn=inner_tick_turn,
                    inner_tick_mode=inner_tick_mode,
                    implicit_signal_bundle=implicit_signal_bundle,
                    force_tools_first_round=force_tools_first_round,
                    companion_llm_client_for_aux=companion_llm_client_for_aux,
                )
            )

        try:
            try:
                if main_event_loop is not None:
                    set_tool_background_db_loop(main_event_loop)
                if langsmith_parent_run is not None:
                    from langsmith.run_helpers import set_tracing_parent

                    with set_tracing_parent(langsmith_parent_run):
                        _run_async_tool_loop()
                else:
                    _run_async_tool_loop()
            except Exception as exc:
                bg_ls_err = repr(exc)
                logger.exception("repl.turn.bg job failed")
                if not exc_chain_includes_llm_inference_failure_root_causes(exc):
                    ev: dict[str, Any] = {
                        "ts": utc_iso_ts(),
                        "kind": "tool_background_failure",
                        "trace_id": trace_id,
                        "user_msg_uuid": user_msg_uuid,
                        "tool_model_name": tool_model_name,
                        "inner_tick_turn": inner_tick_turn,
                        "inner_tick_mode": inner_tick_mode.value,
                        "error_type": type(exc).__name__,
                        "detail": str(exc),
                    }
                    ph = getattr(exc, "provider_http_status", None)
                    if isinstance(ph, int):
                        ev["provider_http_status"] = ph
                    try:
                        append_runtime_event(memory_store, ev)
                    except Exception:
                        logger.warning(
                            "repl.turn.bg append_runtime_event failed trace_id={}",
                            trace_id,
                            exc_info=True,
                        )
            finally:
                end_companion_turn_root_run_safe(
                    langsmith_parent_run,
                    error=bg_ls_err,
                    ls_end_source="tool_background_thread",
                )
                clear_tool_background_db_loop()
        finally:
            companion_llm_runtime_event_bind_ctx.reset(llm_bg_bind_token)
            if tool_bg_idle_event is not None:
                tool_bg_idle_event.set()
            _unregister_thread(threading.current_thread())

    if tool_bg_idle_event is not None:
        tool_bg_idle_event.clear()

    t = threading.Thread(target=_runner, name="inty-v2-tool-bg", daemon=False)
    logger.debug(
        "langsmith_companion_parent_run tool_bg_thread_start inty_trace_id={} "
        "user_msg_uuid={} ls_trace_id={} thread_name={} daemon={}",
        trace_id,
        user_msg_uuid,
        companion_turn_langsmith_parent_trace_id_str(langsmith_parent_run),
        t.name,
        t.daemon,
    )
    t.start()
