"""Companion turn executor: 单轮对话的完整执行流程。

Memory-phase invariant **AwakeTurn**: see ``companion.turn_invariants`` — this module
only appends transcript JSONL on ``MemoryStore``; batch curation belongs in **DreamingBatch**.

可选 ``tool_bg_idle_event``：在加载 transcript 之前等待上一轮 tool_background 收尾，
保证主 ``transcript.jsonl``（或维护内在节拍用的 ``transcript_inner_tick.jsonl``）已含工具摘要后再组装本轮 chat/tool messages。

**Queue-serving turns**: Every track dispatches via ``AgenticLoop.run_single_llm_turn`` or
``AgenticLoop.run_dual_llm_turn`` with a scope ``OutputQueue``. Settled ``USER_CHAT`` routes
via ``user_turn.llm_loop_mode`` to single-LLM or dual-LLM plugin branches; inner ticks and
greeting use ``run_single_llm_turn``.

TODO(#3402): ``UserVisibleChunk`` + single ``UserVisibleChunkSink`` for all queue-serving delivery paths.
TODO(#3398): Dual-LLM user-turn vs single-LLM in-turn sync — epic #3398.

TODO(tool-bg-idle-starves-user-chat): Hung maintenance ``tool_background`` leaves — #3123
``CompanionSession.tool_bg_idle`` cleared; the next proactive or user ``run_turn`` blocks here
while the WebSocket ``turn_lock`` holder waits, so burst USER_MESSAGE can show only
``user-input`` with no ``chat`` (see ``chat.py`` USER_MESSAGE path, ``tool_background.py``).
Issues: https://github.com/NascentCore/inty/issues/3123 (orchestration),
https://github.com/NascentCore/inty/issues/3113 (WS turn_lock).


TODO(#3409): Move this module into a focused sub-package; consider renaming to ``track.py``.

TODO(world-engine-turn-spine): Delegate ``_run_companion_turn_core`` to shared — #3702
AgentHarness turn skeleton via CompanionProfile (epic #3700).
"""

from __future__ import annotations

import asyncio
import contextvars
import os
import threading
import time
import uuid
from contextlib import nullcontext
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.memory.client_time_from_memory_store import (
    resolve_client_time,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from .llm_runtime_events import (
    LlmRuntimeEventBind,
    companion_llm_runtime_event_bind_ctx,
)
from .proactive_chat import build_proactive_chat_transcript_user_marker
from .transcript_ai_private import (
    AiPrivateSplicePersistInput,
    AiPrivateSplicePlan,
    build_ai_private_splice_plan,
    persist_ai_private_splice_if_applicable,
    track_uses_ai_private_splice,
)
from app.core.companion_harness.companion.bootstrap import (
    interactive_bootstrap_active,
)
from .models import (
    CompanionTurnTrack,
    CompanionTurnResult,
    load_context_meta,
    transcript_relative_path_for_turn_persistence,
)
from app.core.companion_harness.loop.track_loop_input import (
    CompanionTurnLoopInput,
)
from app.core.companion_harness.loop.track_loop_plugin import (
    resolve_agentic_loop,
)
from app.core.agentic_companion.types import (
    UserMessageBatch,
    synthetic_user_message_batch,
    user_message_batch_is_agent_initiated_synthetic,
)
from app.core.companion_harness.loop.config import (
    resolved_user_turn_batch_messages_llm_call_mode,
)
from .turn_track import (
    companion_turn_track_skips_empty_proactive_assistant_row,
    companion_turn_track_syncs_transcript_in_agentic_loop,
)
from .turn_deps import CompanionTurnDeps
from .turn_pipeline import (
    CompanionTurnLoadedState,
    CompanionTurnPromptPlan,
    CompanionTurnRuntimeFlags,
    build_companion_turn_prompt_plan,
    load_companion_turn_state,
    resolve_turn_runtime_flags,
)
from .models import ContextMeta
from .turn_tail_user import TurnTailUserMessage
from .turn_tail_user import (
    append_turn_track_tail_user_transcript_rows,
    resolve_turn_tail_user_messages,
)
from .transcript_assistant_row import (
    TranscriptAssistantRowBuildInput,
    append_transcript_assistant_row,
)
from .utc import (
    strip_leading_transcript_timestamp_prefixes,
    utc_iso_ts,
    utc_now,
)
from .implicit_signal_messages import (
    USER_SIGNED_ON_TRIGGER_USER_TEXT,
    implicit_user_signed_on_chat_turn,
)
from .inner_tick_schedule import transcript_tail_message_uuid
from .llm_chat_runtime import (
    companion_turn_langsmith_parent_trace_id_str,
    create_companion_turn_root_run,
    end_companion_turn_root_run_safe,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


def _enrich_companion_turn_deps_client_time(
    deps: CompanionTurnDeps,
) -> CompanionTurnDeps:
    """Resolve client time from MemoryStore and merge into runtime_context."""
    runtime_context = deps.runtime_context
    incoming_bundle = runtime_context.implicit_signal_bundle
    resolved_time = resolve_client_time(
        store=deps.store,
        incoming=(
            incoming_bundle.client_time if incoming_bundle is not None else None
        ),
        default_user_time_zone=(
            global_config_loaded_from_config_yaml.agent.companion_harness.default_user_time_zone
        ),
    )
    if resolved_time is None:
        return deps
    if incoming_bundle is None:
        enriched_bundle = ImplicitSignalBundle(client_time=resolved_time)
    else:
        enriched_bundle = incoming_bundle.model_copy(
            update={"client_time": resolved_time}
        )
    runtime_context = replace(
        runtime_context,
        implicit_signal_bundle=enriched_bundle,
    )
    return replace(deps, runtime_context=runtime_context)


def _resolve_tool_bg_idle_wait_timeout_sec(llm_client: Any) -> float:
    raw_idle_timeout = (
        os.environ.get("INTY_TOOL_BG_IDLE_WAIT_TIMEOUT_SEC", "").strip() or ""
    )
    try:
        return (
            float(raw_idle_timeout)
            if raw_idle_timeout
            else float(llm_client.config.async_chat_front_timeout_sec)
        )
    except ValueError:
        return float(llm_client.config.async_chat_front_timeout_sec)


async def _maybe_await_tool_bg_idle_before_turn(
    *,
    track: CompanionTurnTrack,
    tool_bg_idle_event: threading.Event | None,
    idle_wait_timeout_sec: float,
    scope_registry_key: str,
) -> None:
    """User/proactive turns skip idle wait so burst USER_CHAT is not starved."""
    match track:
        case (
            CompanionTurnTrack.USER_CHAT
            | CompanionTurnTrack.USER_CHAT_BOOTSTRAP
            | CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
            | CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
        ):
            return
        case _:
            await _await_tool_background_idle_if_configured(
                tool_bg_idle_event,
                idle_wait_timeout_sec=idle_wait_timeout_sec,
                scope_registry_key=scope_registry_key,
            )


@dataclass(frozen=True)
class _CompanionTurnAgenticLoopOutcome:
    assistant_text: str
    significance_meta: dict[str, Any] | None
    turn_recall: str | None
    langsmith_trace_id: str
    langsmith_run_id: str
    skip_final_transcript_assistant_row: bool
    last_interim_assistant_msg_uuid: str | None
    output_message_ids: tuple[str, ...]
    tool_background_started: bool
    skip_proactive_assistant_transcript_row: bool


@dataclass(frozen=True)
class _CompanionTurnLangsmithParentBinding:
    parent_run: Any | None
    langsmith_trace_id: str
    tracing_context: Any


def _bind_companion_turn_langsmith_parent(
    *,
    prepared: CompanionTurnLoopInput,
    langsmith_parent_run_enabled: bool,
    inner_tick_turn: bool,
    route_inner_activity: Any,
    implicit_sign_on_turn: bool,
    store: Any,
    trace_id: str,
    user_msg_uuid: str,
    track: CompanionTurnTrack,
) -> _CompanionTurnLangsmithParentBinding:
    langsmith_parent_run = create_companion_turn_root_run(
        inty_trace_id=trace_id,
        user_msg_uuid=user_msg_uuid,
        chat_model=prepared.llm_client.resolve_model("chat"),
        tool_model=prepared.llm_client.resolve_model("tool"),
        user_id=prepared.loaded_state.context.user_id,
        companion_id=prepared.loaded_state.context.companion_id,
        parent_run_enabled=langsmith_parent_run_enabled,
        companion_turn_track=track,
        inner_tick_turn=inner_tick_turn,
        inner_tick_activity=(
            route_inner_activity if inner_tick_turn else None
        ),
        implicit_user_signed_on=implicit_sign_on_turn,
        transcript_newest_message_uuid=(
            transcript_tail_message_uuid(store) if inner_tick_turn else None
        ),
        langsmith_slice=prepared.langsmith_slice,
    )
    langsmith_trace_acc = prepared.langsmith_trace_id
    _ls_tid = companion_turn_langsmith_parent_trace_id_str(langsmith_parent_run)
    if _ls_tid:
        langsmith_trace_acc = _ls_tid
    if langsmith_parent_run is not None:
        logger.debug(
            "langsmith_companion_parent_run run_turn_bind inty_trace_id={} "
            "user_msg_uuid={} ls_trace_id={} defer_end_to_bg={}",
            trace_id,
            user_msg_uuid,
            _ls_tid,
            bool(prepared.tools_for_turn),
        )
    tracing_context = nullcontext()
    if langsmith_parent_run is not None:
        from langsmith.run_helpers import tracing_context as langsmith_tracing_context

        tracing_context = langsmith_tracing_context(parent=langsmith_parent_run)
    return _CompanionTurnLangsmithParentBinding(
        parent_run=langsmith_parent_run,
        langsmith_trace_id=langsmith_trace_acc,
        tracing_context=tracing_context,
    )


async def _invoke_companion_turn_plugin(
    *,
    prepared: CompanionTurnLoopInput,
    track: CompanionTurnTrack,
    t_loop_start: float,
) -> _CompanionTurnAgenticLoopOutcome:
    plugin = resolve_agentic_loop(track=track)
    loop_out = await plugin.run(prepared)
    skip_proactive_assistant_transcript_row = False
    if (
        companion_turn_track_skips_empty_proactive_assistant_row(track)
        and not loop_out.assistant_text.strip()
    ):
        skip_proactive_assistant_transcript_row = True
    logger.info(
        "run_turn loop_done agentic_loop track={} loop_total_ms={:.0f}",
        track.value,
        (time.perf_counter() - t_loop_start) * 1000.0,
    )
    return _CompanionTurnAgenticLoopOutcome(
        assistant_text=loop_out.assistant_text,
        significance_meta=loop_out.significance_meta,
        turn_recall=loop_out.turn_recall,
        langsmith_trace_id=loop_out.langsmith_trace_id,
        langsmith_run_id=loop_out.langsmith_run_id,
        skip_final_transcript_assistant_row=loop_out.skip_final_transcript_assistant_row,
        last_interim_assistant_msg_uuid=loop_out.last_interim_assistant_msg_uuid,
        output_message_ids=loop_out.output_message_ids,
        tool_background_started=loop_out.tool_background_started,
        skip_proactive_assistant_transcript_row=skip_proactive_assistant_transcript_row,
    )


async def _run_companion_turn_agentic_loop(
    *,
    prepared: CompanionTurnLoopInput,
    langsmith_parent_run_enabled: bool,
    inner_tick_turn: bool,
    route_inner_activity: Any,
    implicit_sign_on_turn: bool,
    store: Any,
    trace_id: str,
    user_msg_uuid: str,
    track: CompanionTurnTrack,
    t_loop_start: float,
) -> _CompanionTurnAgenticLoopOutcome:
    binding = _bind_companion_turn_langsmith_parent(
        prepared=prepared,
        langsmith_parent_run_enabled=langsmith_parent_run_enabled,
        inner_tick_turn=inner_tick_turn,
        route_inner_activity=route_inner_activity,
        implicit_sign_on_turn=implicit_sign_on_turn,
        store=store,
        trace_id=trace_id,
        user_msg_uuid=user_msg_uuid,
        track=track,
    )
    with binding.tracing_context:
        try:
            return await _invoke_companion_turn_plugin(
                prepared=prepared,
                track=track,
                t_loop_start=t_loop_start,
            )
        except BaseException as exc:
            end_companion_turn_root_run_safe(
                binding.parent_run,
                error=repr(exc),
                ls_end_source="run_turn_sync_exc",
            )
            raise
        else:
            end_companion_turn_root_run_safe(
                binding.parent_run, ls_end_source="run_turn_sync_ok"
            )


def _companion_turn_transcript_relative_path(
    *,
    track: CompanionTurnTrack,
    implicit_sign_on_turn: bool,
) -> str:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    if implicit_sign_on_turn:
        return paths.transcript
    return transcript_relative_path_for_turn_persistence(track=track)


def _resolve_companion_turn_assistant_msg_uuid(
    last_interim_assistant_msg_uuid: str | None,
) -> str:
    if last_interim_assistant_msg_uuid is not None:
        return last_interim_assistant_msg_uuid
    return str(uuid.uuid4())


def _append_companion_turn_user_transcript_side(
    *,
    store: Any,
    rel_tr: str,
    track: CompanionTurnTrack,
    implicit_sign_on_turn: bool,
    in_turn_sync_persisted_transcript: bool,
    tail_user_messages: Any,
    trace_id: str,
    user_msg_uuid: str,
    ts_user: Any,
) -> None:
    if implicit_sign_on_turn:
        sign_on_row: dict[str, Any] = {
            "role": "user",
            "content": USER_SIGNED_ON_TRIGGER_USER_TEXT,
            "ts": ts_user.isoformat(),
            "uuid": user_msg_uuid,
            "trace_id": trace_id,
            "implicit_user_signed_on": True,
        }
        store.append_jsonl_record(rel_tr, sign_on_row)
        return
    if in_turn_sync_persisted_transcript:
        return
    append_turn_track_tail_user_transcript_rows(
        store,
        rel_tr,
        tail_user_messages=tail_user_messages,
        trace_id=trace_id,
        track=track,
    )


def _append_companion_turn_final_assistant_transcript_row(
    *,
    store: Any,
    rel_tr: str,
    assistant_msg_uuid: str,
    user_msg_uuid: str,
    trace_id: str,
    last_text: str,
    skip_final_transcript_assistant_row: bool,
    skip_proactive_assistant_transcript_row: bool,
    significance_meta: dict[str, Any] | None,
    turn_recall: str | None,
    inner_tick_turn: bool,
) -> None:
    if skip_final_transcript_assistant_row:
        return
    if skip_proactive_assistant_transcript_row:
        return
    append_transcript_assistant_row(
        store,
        rel_tr,
        TranscriptAssistantRowBuildInput(
            content=last_text,
            uuid=assistant_msg_uuid,
            reply_to=user_msg_uuid,
            trace_id=trace_id,
            source="inner_tick" if inner_tick_turn else "chat",
            significance_perception=significance_meta,
            turn_recall=turn_recall,
        ),
        ts=utc_iso_ts(),
    )


def _persist_companion_turn_transcript(
    *,
    store: Any,
    track: CompanionTurnTrack,
    implicit_sign_on_turn: bool,
    in_turn_sync_persisted_transcript: bool,
    tail_user_messages: Any,
    trace_id: str,
    user_msg_uuid: str,
    ts_user: Any,
    ai_private_splice_plan: AiPrivateSplicePlan,
    last_text: str,
    skip_final_transcript_assistant_row: bool,
    skip_proactive_assistant_transcript_row: bool,
    last_interim_assistant_msg_uuid: str | None,
    significance_meta: dict[str, Any] | None,
    turn_recall: str | None,
    inner_tick_turn: bool,
) -> str:
    rel_tr = _companion_turn_transcript_relative_path(
        track=track,
        implicit_sign_on_turn=implicit_sign_on_turn,
    )
    assistant_msg_uuid = _resolve_companion_turn_assistant_msg_uuid(
        last_interim_assistant_msg_uuid
    )
    _append_companion_turn_user_transcript_side(
        store=store,
        rel_tr=rel_tr,
        track=track,
        implicit_sign_on_turn=implicit_sign_on_turn,
        in_turn_sync_persisted_transcript=in_turn_sync_persisted_transcript,
        tail_user_messages=tail_user_messages,
        trace_id=trace_id,
        user_msg_uuid=user_msg_uuid,
        ts_user=ts_user,
    )
    last_text = strip_leading_transcript_timestamp_prefixes(last_text)
    persist_ai_private_splice_if_applicable(
        AiPrivateSplicePersistInput(
            store=store,
            transcript_relative_path=rel_tr,
            track=track,
            splice_plan=ai_private_splice_plan,
            user_msg_uuid=user_msg_uuid,
            assistant_text=last_text,
            skip_final_transcript_assistant_row=skip_final_transcript_assistant_row,
        )
    )
    _append_companion_turn_final_assistant_transcript_row(
        store=store,
        rel_tr=rel_tr,
        assistant_msg_uuid=assistant_msg_uuid,
        user_msg_uuid=user_msg_uuid,
        trace_id=trace_id,
        last_text=last_text,
        skip_final_transcript_assistant_row=skip_final_transcript_assistant_row,
        skip_proactive_assistant_transcript_row=skip_proactive_assistant_transcript_row,
        significance_meta=significance_meta,
        turn_recall=turn_recall,
        inner_tick_turn=inner_tick_turn,
    )
    return assistant_msg_uuid


async def _await_tool_background_idle_if_configured(
    tool_bg_idle_event: threading.Event | None,
    *,
    idle_wait_timeout_sec: float,
    scope_registry_key: str,
) -> None:
    # TODO(tool-bg-idle-starves-user-chat): Timeout logs WARNING but still proceeds; — #3123
    # a stuck tool_bg thread can wedge every later turn on this session until restart.
    # https://github.com/NascentCore/inty/issues/3123
    if tool_bg_idle_event is None:
        return

    def _wait() -> bool:
        return tool_bg_idle_event.wait(timeout=idle_wait_timeout_sec)

    ok = await asyncio.to_thread(_wait)
    if not ok:
        logger.warning(
            "run_turn tool_bg_idle wait timed out after {:.2f}s scope={}",
            idle_wait_timeout_sec,
            scope_registry_key,
        )


@dataclass(frozen=True)
class _CompanionTurnPrepared:
    """Front-half state for one companion turn before the agentic LLM phase."""

    track: CompanionTurnTrack
    deps: CompanionTurnDeps
    store: Any
    runtime_flags: CompanionTurnRuntimeFlags
    loaded_state: CompanionTurnLoadedState
    context: ContextMeta
    tail_user_messages: tuple[TurnTailUserMessage, ...]
    user_msg_uuid: str
    user_message_batch: UserMessageBatch | None
    prompt_plan: CompanionTurnPromptPlan
    trace_id: str
    user_text: str
    ts_user: datetime
    ai_private_splice_plan: AiPrivateSplicePlan
    in_turn_sync_persisted_transcript: bool
    messages: list[dict[str, Any]]
    tools_for_turn: list[dict[str, Any]]


@dataclass(frozen=True)
class _CompanionTurnUserTailContext:
    """Loaded transcript state, tail user rows, and InputQueue batch correlation."""

    loaded_state: CompanionTurnLoadedState
    context: ContextMeta
    user_text: str
    user_msg_uuid: str
    tail_user_messages: tuple[TurnTailUserMessage, ...]
    user_message_batch: UserMessageBatch | None
    ai_private_splice_plan: AiPrivateSplicePlan
    ts_user: datetime


def _log_companion_turn_prepare_start(
    *,
    store: Any,
    track: CompanionTurnTrack,
    user_text: str,
    inner_tick_turn: bool,
    route_inner_activity: Any,
    llm_client: Any,
) -> None:
    logger.info(
        "run_turn start scope={} track={} user_chars={} inner_tick_turn={} inner_tick_activity={}",
        store.scope.registry_key(),
        track.value,
        len(user_text),
        inner_tick_turn,
        route_inner_activity.value if inner_tick_turn else "-",
    )
    logger.debug(
        "run_turn llm_client api_base={} model_chat={} model_tool={} dual_llm=True",
        llm_client.config.api_base,
        llm_client.resolve_model("chat"),
        llm_client.resolve_model("tool"),
    )


@dataclass(frozen=True)
class _CompanionTurnTailLoadedBundle:
    loaded_state: CompanionTurnLoadedState
    user_text: str
    ai_private_splice_plan: AiPrivateSplicePlan


def _load_companion_turn_tail_loaded_bundle(
    *,
    store: Any,
    track: CompanionTurnTrack,
    runtime_flags: CompanionTurnRuntimeFlags,
    user_text: str,
    transcript_llm_window_max_messages: int,
) -> _CompanionTurnTailLoadedBundle:
    loaded_state = load_companion_turn_state(
        store=store,
        track=track,
        transcript_llm_window_max_messages=transcript_llm_window_max_messages,
    )
    if runtime_flags.tick_proactive:
        user_text = build_proactive_chat_transcript_user_marker(
            loaded_state.loaded_transcript
        )
    ai_private_splice_plan = AiPrivateSplicePlan(
        thoughts=(), anchor_user_msg_uuid=None
    )
    if track_uses_ai_private_splice(track):
        ai_private_splice_plan = build_ai_private_splice_plan(
            store, loaded_state.loaded_transcript
        )
    return _CompanionTurnTailLoadedBundle(
        loaded_state=loaded_state,
        user_text=user_text,
        ai_private_splice_plan=ai_private_splice_plan,
    )


def _resolve_companion_turn_user_message_batch(
    *,
    track: CompanionTurnTrack,
    user_msg_uuid: str,
    user_message_batch: UserMessageBatch | None,
) -> UserMessageBatch | None:
    if track == CompanionTurnTrack.USER_CHAT_BOOTSTRAP and (
        user_message_batch is None
        or user_message_batch_is_agent_initiated_synthetic(user_message_batch)
    ):
        raise RuntimeError(
            "USER_CHAT_BOOTSTRAP requires queue-serving InputQueue batch "
            "correlation; direct synthetic batch is not supported (#3466)."
        )
    if track == CompanionTurnTrack.USER_CHAT and user_message_batch is None:
        return synthetic_user_message_batch(
            user_msg_uuid=user_msg_uuid,
            track_label=track.value,
        )
    return user_message_batch


def _resolve_companion_turn_user_tail_context(
    *,
    store: Any,
    track: CompanionTurnTrack,
    runtime_flags: CompanionTurnRuntimeFlags,
    user_text: str,
    transcript_llm_window_max_messages: int,
    preset_user_msg_uuid: str | None,
    input_batch: Any,
    user_message_batch: UserMessageBatch | None,
) -> _CompanionTurnUserTailContext:
    tail_bundle = _load_companion_turn_tail_loaded_bundle(
        store=store,
        track=track,
        runtime_flags=runtime_flags,
        user_text=user_text,
        transcript_llm_window_max_messages=transcript_llm_window_max_messages,
    )
    loaded_state = tail_bundle.loaded_state
    user_text = tail_bundle.user_text
    context = loaded_state.context
    ts_user = utc_now()
    user_msg_uuid = (
        preset_user_msg_uuid if preset_user_msg_uuid else str(uuid.uuid4())
    )
    implicit_sign_on_turn = runtime_flags.implicit_sign_on_turn
    tail_user_messages = resolve_turn_tail_user_messages(
        mode=resolved_user_turn_batch_messages_llm_call_mode(),
        input_batch=input_batch,
        user_text=(
            USER_SIGNED_ON_TRIGGER_USER_TEXT
            if implicit_sign_on_turn
            else user_text
        ),
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        implicit_sign_on_turn=implicit_sign_on_turn,
    )
    user_msg_uuid = tail_user_messages[-1].message_id
    user_message_batch = _resolve_companion_turn_user_message_batch(
        track=track,
        user_msg_uuid=user_msg_uuid,
        user_message_batch=user_message_batch,
    )
    return _CompanionTurnUserTailContext(
        loaded_state=loaded_state,
        context=context,
        user_text=user_text,
        user_msg_uuid=user_msg_uuid,
        tail_user_messages=tail_user_messages,
        user_message_batch=user_message_batch,
        ai_private_splice_plan=tail_bundle.ai_private_splice_plan,
        ts_user=ts_user,
    )


def _build_companion_turn_prompt_plan_for_prepare(
    *,
    store: Any,
    tail_ctx: _CompanionTurnUserTailContext,
    track: CompanionTurnTrack,
    runtime_flags: CompanionTurnRuntimeFlags,
    runtime_context: Any,
    transcript_compaction: Any,
) -> CompanionTurnPromptPlan:
    return build_companion_turn_prompt_plan(
        store=store,
        loaded_state=tail_ctx.loaded_state,
        tail_user_messages=tail_ctx.tail_user_messages,
        track=track,
        tick_proactive=runtime_flags.tick_proactive,
        implicit_sign_on_turn=runtime_flags.implicit_sign_on_turn,
        runtime_context=runtime_context,
        transcript_compaction=transcript_compaction,
        tail_splice_thoughts=list(tail_ctx.ai_private_splice_plan.thoughts),
    )


async def _resolve_companion_turn_idle_and_user_tail(
    *,
    track: CompanionTurnTrack,
    llm_client: Any,
    tool_bg_idle_event: threading.Event | None,
    store: Any,
    runtime_flags: CompanionTurnRuntimeFlags,
    user_text: str,
    transcript_llm_window_max_messages: int,
    preset_user_msg_uuid: str | None,
    input_batch: Any,
    user_message_batch: UserMessageBatch | None,
) -> _CompanionTurnUserTailContext:
    idle_wait_timeout_sec = _resolve_tool_bg_idle_wait_timeout_sec(llm_client)
    await _maybe_await_tool_bg_idle_before_turn(
        track=track,
        tool_bg_idle_event=tool_bg_idle_event,
        idle_wait_timeout_sec=idle_wait_timeout_sec,
        scope_registry_key=store.scope.registry_key(),
    )
    return _resolve_companion_turn_user_tail_context(
        store=store,
        track=track,
        runtime_flags=runtime_flags,
        user_text=user_text,
        transcript_llm_window_max_messages=transcript_llm_window_max_messages,
        preset_user_msg_uuid=preset_user_msg_uuid,
        input_batch=input_batch,
        user_message_batch=user_message_batch,
    )


def _assemble_companion_turn_prepared(
    *,
    track: CompanionTurnTrack,
    deps: CompanionTurnDeps,
    store: Any,
    runtime_flags: CompanionTurnRuntimeFlags,
    tail_ctx: _CompanionTurnUserTailContext,
    prompt_plan: CompanionTurnPromptPlan,
    trace_id: str,
) -> _CompanionTurnPrepared:
    in_turn_sync_persisted_transcript = (
        companion_turn_track_syncs_transcript_in_agentic_loop(track)
    )
    return _CompanionTurnPrepared(
        track=track,
        deps=deps,
        store=store,
        runtime_flags=runtime_flags,
        loaded_state=tail_ctx.loaded_state,
        context=tail_ctx.context,
        tail_user_messages=tail_ctx.tail_user_messages,
        user_msg_uuid=tail_ctx.user_msg_uuid,
        user_message_batch=tail_ctx.user_message_batch,
        prompt_plan=prompt_plan,
        trace_id=trace_id,
        user_text=tail_ctx.user_text,
        ts_user=tail_ctx.ts_user,
        ai_private_splice_plan=tail_ctx.ai_private_splice_plan,
        in_turn_sync_persisted_transcript=in_turn_sync_persisted_transcript,
        messages=prompt_plan.messages,
        tools_for_turn=prompt_plan.tools_for_turn,
    )


async def _prepare_companion_turn_execution(
    user_text: str,
    *,
    track: CompanionTurnTrack,
    deps: CompanionTurnDeps,
) -> _CompanionTurnPrepared:
    deps = _enrich_companion_turn_deps_client_time(deps)
    store = deps.store
    llm_client = deps.llm_client
    transcript_compaction = deps.transcript_compaction
    transcript_llm_window_max_messages = deps.transcript_llm_window_max_messages
    runtime_context = deps.runtime_context
    preset_user_msg_uuid = deps.preset_user_msg_uuid
    tool_bg_idle_event = deps.tool_bg_idle_event
    user_message_batch = deps.user_message_batch
    input_batch = deps.input_batch
    implicit_signal_bundle = runtime_context.implicit_signal_bundle

    runtime_flags = resolve_turn_runtime_flags(
        track=track,
        user_text=user_text,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    user_text = runtime_flags.effective_user_text
    inner_tick_turn = runtime_flags.inner_tick_turn

    _log_companion_turn_prepare_start(
        store=store,
        track=track,
        user_text=user_text,
        inner_tick_turn=inner_tick_turn,
        route_inner_activity=runtime_flags.route_inner_activity,
        llm_client=llm_client,
    )

    tail_ctx = await _resolve_companion_turn_idle_and_user_tail(
        track=track,
        llm_client=llm_client,
        tool_bg_idle_event=tool_bg_idle_event,
        store=store,
        runtime_flags=runtime_flags,
        user_text=user_text,
        transcript_llm_window_max_messages=transcript_llm_window_max_messages,
        preset_user_msg_uuid=preset_user_msg_uuid,
        input_batch=input_batch,
        user_message_batch=user_message_batch,
    )
    prompt_plan = _build_companion_turn_prompt_plan_for_prepare(
        store=store,
        tail_ctx=tail_ctx,
        track=track,
        runtime_flags=runtime_flags,
        runtime_context=runtime_context,
        transcript_compaction=transcript_compaction,
    )
    trace_id = str(uuid.uuid4())
    return _assemble_companion_turn_prepared(
        track=track,
        deps=deps,
        store=store,
        runtime_flags=runtime_flags,
        tail_ctx=tail_ctx,
        prompt_plan=prompt_plan,
        trace_id=trace_id,
    )


def _companion_turn_transcript_rel_for_loop(
    track: CompanionTurnTrack,
) -> str:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    if track == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
        return paths.transcript
    return transcript_relative_path_for_turn_persistence(track=track)


def _companion_turn_llm_runtime_bind_enter(
    *,
    store: Any,
    trace_id: str,
    user_msg_uuid: str,
    inner_tick_turn: bool,
) -> contextvars.Token[LlmRuntimeEventBind | None]:
    _llm_ev_phase = "inner_tick" if inner_tick_turn else "foreground_chat"
    return companion_llm_runtime_event_bind_ctx.set(
        LlmRuntimeEventBind(
            memory_store=store,
            trace_id=trace_id,
            user_msg_uuid=user_msg_uuid,
            phase=_llm_ev_phase,
            scene=None,
        )
    )


def _build_companion_turn_loop_input(
    prepared: _CompanionTurnPrepared,
) -> CompanionTurnLoopInput:
    deps = prepared.deps
    runtime_flags = prepared.runtime_flags
    return CompanionTurnLoopInput(
        store=prepared.store,
        llm_client=deps.llm_client,
        track=prepared.track,
        runtime_flags=runtime_flags,
        loaded_state=prepared.loaded_state,
        prompt_plan=prepared.prompt_plan,
        tail_user_messages=prepared.tail_user_messages,
        messages=prepared.messages,
        tools_for_turn=prepared.tools_for_turn,
        trace_id=prepared.trace_id,
        langsmith_slice=deps.langsmith_slice,
        runtime_context=deps.runtime_context,
        agentic_output_queue=deps.agentic_output_queue,
        user_message_batch=prepared.user_message_batch,
        user_text=prepared.user_text,
        ts_user=prepared.ts_user,
        user_msg_uuid=prepared.user_msg_uuid,
        ai_private_splice_plan=prepared.ai_private_splice_plan,
        repository_only_store_text=deps.repository_only_store_text,
        langsmith_trace_id="",
        langsmith_run_id="",
        transcript_rel=_companion_turn_transcript_rel_for_loop(prepared.track),
    )


async def _run_companion_turn_agentic_phase(
    *,
    prepared: _CompanionTurnPrepared,
    t_loop_start: float,
) -> _CompanionTurnAgenticLoopOutcome:
    deps = prepared.deps
    runtime_flags = prepared.runtime_flags
    inner_tick_turn = runtime_flags.inner_tick_turn
    route_inner_activity = runtime_flags.route_inner_activity
    implicit_sign_on_turn = runtime_flags.implicit_sign_on_turn
    llm_runtime_bind_token: (
        contextvars.Token[LlmRuntimeEventBind | None] | None
    ) = None
    try:
        llm_runtime_bind_token = _companion_turn_llm_runtime_bind_enter(
            store=prepared.store,
            trace_id=prepared.trace_id,
            user_msg_uuid=prepared.user_msg_uuid,
            inner_tick_turn=inner_tick_turn,
        )
        loop_input = _build_companion_turn_loop_input(prepared)
        return await _run_companion_turn_agentic_loop(
            prepared=loop_input,
            langsmith_parent_run_enabled=deps.langsmith_parent_run_enabled,
            inner_tick_turn=inner_tick_turn,
            route_inner_activity=route_inner_activity,
            implicit_sign_on_turn=implicit_sign_on_turn,
            store=prepared.store,
            trace_id=prepared.trace_id,
            user_msg_uuid=prepared.user_msg_uuid,
            track=prepared.track,
            t_loop_start=t_loop_start,
        )
    finally:
        if llm_runtime_bind_token is not None:
            companion_llm_runtime_event_bind_ctx.reset(llm_runtime_bind_token)


def _companion_turn_result_from_outcome(
    *,
    prepared: _CompanionTurnPrepared,
    loop_outcome: _CompanionTurnAgenticLoopOutcome,
    assistant_msg_uuid: str,
    t0: float,
) -> CompanionTurnResult:
    implicit_sign_on_turn = prepared.runtime_flags.implicit_sign_on_turn
    inner_tick_turn = prepared.runtime_flags.inner_tick_turn
    route_inner_activity = prepared.runtime_flags.route_inner_activity
    logger.info(
        "run_turn done assistant_chars={} ms={:.0f} inty_trace_id={} user_msg_uuid={} "
        "langsmith_trace_id={} langsmith_run_id={}",
        len(loop_outcome.assistant_text),
        (time.perf_counter() - t0) * 1000.0,
        prepared.trace_id,
        prepared.user_msg_uuid,
        loop_outcome.langsmith_trace_id or "",
        loop_outcome.langsmith_run_id or "",
    )
    transcript_user_content = (
        USER_SIGNED_ON_TRIGGER_USER_TEXT
        if implicit_sign_on_turn
        else "\n".join(message.text for message in prepared.tail_user_messages)
    )
    return CompanionTurnResult(
        assistant_text=loop_outcome.assistant_text,
        significance_perception=loop_outcome.significance_meta,
        turn_recall=loop_outcome.turn_recall,
        user_msg_uuid=prepared.user_msg_uuid,
        assistant_msg_uuid=assistant_msg_uuid,
        trace_id=prepared.trace_id,
        langsmith_trace_id=loop_outcome.langsmith_trace_id,
        langsmith_run_id=loop_outcome.langsmith_run_id,
        tool_background_started=loop_outcome.tool_background_started,
        assistant_source=prepared.runtime_flags.turn_type,
        inner_tick_activity=(
            route_inner_activity.value if inner_tick_turn else None
        ),
        turn_start_context_mode=prepared.context.context_mode,
        transcript_compaction=prepared.prompt_plan.transcript_compaction,
        transcript_user_content=transcript_user_content,
        output_message_ids=loop_outcome.output_message_ids,
    )


# TODO(companion-multimodal-user-turn): Phase 1c — ``user_turn: CompanionUserTurnInput`` — #3293
# https://github.com/NascentCore/inty/issues/3293
# through turn core; transcript user row uses ``user_turn.to_transcript_text()`` (caption
# or ``"[image]"``); memory pipeline stays text-only. LLM tail content assembled in
# turn_pipeline when chat model accepts IMAGE input.
# TODO(track-driven-system-messages-building): Inline calling of this function in the callers. — #3453
async def _run_companion_turn_core(
    user_text: str,
    *,
    track: CompanionTurnTrack,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    # TODO(#3473): skip LLM when companion_token_budget_allows_llm is false.
    """
    执行一轮完整对话。

    - 加载 context + prompt bundle + transcript
    - 组装 system prompt + messages
    - 调用 LLM（经 ``AgenticLoop`` + ``OutputQueue``）
    - 持久化 transcript

    返回 ``CompanionTurnResult``（``assistant_text`` 与可选 ``significance_perception``）。
    """
    assert deps.agentic_output_queue is not None
    t0 = time.perf_counter()
    prepared = await _prepare_companion_turn_execution(
        user_text,
        track=track,
        deps=deps,
    )
    t_loop = time.perf_counter()
    loop_outcome = await _run_companion_turn_agentic_phase(
        prepared=prepared,
        t_loop_start=t_loop,
    )
    implicit_sign_on_turn = prepared.runtime_flags.implicit_sign_on_turn
    inner_tick_turn = prepared.runtime_flags.inner_tick_turn
    assistant_msg_uuid = _persist_companion_turn_transcript(
        store=prepared.store,
        track=prepared.track,
        implicit_sign_on_turn=implicit_sign_on_turn,
        in_turn_sync_persisted_transcript=prepared.in_turn_sync_persisted_transcript,
        tail_user_messages=prepared.tail_user_messages,
        trace_id=prepared.trace_id,
        user_msg_uuid=prepared.user_msg_uuid,
        ts_user=prepared.ts_user,
        ai_private_splice_plan=prepared.ai_private_splice_plan,
        last_text=loop_outcome.assistant_text,
        skip_final_transcript_assistant_row=loop_outcome.skip_final_transcript_assistant_row,
        skip_proactive_assistant_transcript_row=loop_outcome.skip_proactive_assistant_transcript_row,
        last_interim_assistant_msg_uuid=loop_outcome.last_interim_assistant_msg_uuid,
        significance_meta=loop_outcome.significance_meta,
        turn_recall=loop_outcome.turn_recall,
        inner_tick_turn=inner_tick_turn,
    )
    return _companion_turn_result_from_outcome(
        prepared=prepared,
        loop_outcome=loop_outcome,
        assistant_msg_uuid=assistant_msg_uuid,
        t0=t0,
    )


async def run_companion_user_chat_turn(
    user_text: str,
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    implicit_signal_bundle = deps.runtime_context.implicit_signal_bundle
    if (
        implicit_signal_bundle is not None
        and implicit_user_signed_on_chat_turn(
            implicit_signal_bundle=implicit_signal_bundle,
            inner_tick_turn=False,
        )
    ):
        raise ValueError(
            "implicit sign-on greeting must use run_companion_implicit_sign_on_greeting_turn"
        )
    context = load_context_meta(store=deps.store)
    track = (
        CompanionTurnTrack.USER_CHAT_BOOTSTRAP
        if interactive_bootstrap_active(meta=context)
        else CompanionTurnTrack.USER_CHAT
    )
    return await _run_companion_turn_core(user_text, track=track, deps=deps)


async def run_companion_implicit_sign_on_greeting_turn(
    user_text: str,
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    implicit_signal_bundle = deps.runtime_context.implicit_signal_bundle
    assert implicit_signal_bundle is not None
    assert implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=implicit_signal_bundle,
        inner_tick_turn=False,
    )
    return await _run_companion_turn_core(
        user_text,
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
        deps=deps,
    )


async def run_companion_inner_tick_proactive_chat_turn(
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    return await _run_companion_turn_core(
        "",
        track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        deps=deps,
    )


async def run_companion_inner_tick_scheduled_turn(
    scheduled_user_text: str,
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    assert (
        scheduled_user_text.strip()
    ), "run_companion_inner_tick_scheduled_turn requires non-empty scheduled_user_text"
    return await _run_companion_turn_core(
        scheduled_user_text,
        track=CompanionTurnTrack.INNER_TICK_SCHEDULED,
        deps=deps,
    )


async def run_companion_inner_tick_monolog_turn(
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    return await _run_companion_turn_core(
        "",
        track=CompanionTurnTrack.INNER_TICK_MONOLOG,
        deps=deps,
    )


async def run_inner_tick_autonomy(
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    """AUTONOMY inner tick: open tool set, **never** delivers to the user.

    Same async foreground/tool-background lifecycle as monolog, but with
    an open tool set and the autonomy system prompt slice that instructs the
    model to read ``LIFE_CURRENTS.md``, do real work (web, image, MemoryStore
    writes), and write progress back — all silently.
    """
    return await _run_companion_turn_core(
        "",
        track=CompanionTurnTrack.INNER_TICK_AUTONOMY,
        deps=deps,
    )
