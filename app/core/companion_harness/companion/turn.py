"""Companion turn executor: 单轮对话的完整执行流程。

Memory-phase invariant **AwakeTurn**: see ``companion.turn_invariants`` — this module
only appends transcript JSONL on ``MemoryStore``; batch curation belongs in **DreamingBatch**.

可选 ``tool_bg_idle_event``：在加载 transcript 之前等待上一轮 tool_background 收尾，
保证主 ``transcript.jsonl``（或维护内在节拍用的 ``transcript_inner_tick.jsonl``）已含工具摘要后再组装本轮 chat/tool messages。

**Queue-serving turns**: Every track dispatches via ``AgenticLoop.run_single_llm_turn`` or
``AgenticLoop.run_dual_llm_turn`` with a scope ``OutputQueue``. Settled ``USER_CHAT`` routes
via ``user_turn.llm_loop_mode`` to single-LLM or dual-LLM plugin branches; inner ticks and
greeting use ``run_single_llm_turn``.

TODO(!3402): ``UserVisibleChunk`` + single ``UserVisibleChunkSink`` for all queue-serving delivery paths.
TODO(!3398): Dual-LLM user-turn vs single-LLM in-turn sync — epic #3398, #3369.

TODO(tool-bg-idle-starves-user-chat): Hung maintenance ``tool_background`` leaves — #3123
``CompanionSession.tool_bg_idle`` cleared; the next proactive or user ``run_turn`` blocks here
while the WebSocket ``turn_lock`` holder waits, so burst USER_MESSAGE can show only
``user-input`` with no ``chat`` (see ``chat.py`` USER_MESSAGE path, ``tool_background.py``).
Issues: https://github.com/NascentCore/inty/issues/3123 (orchestration),
https://github.com/NascentCore/inty/issues/3113 (WS turn_lock).


TODO(!3409): Move this module into a focused sub-package; consider renaming to ``track.py``.

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
from dataclasses import replace
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
from app.core.companion_harness.agentic_companion.types import (
    synthetic_user_message_batch,
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
    build_companion_turn_prompt_plan,
    load_companion_turn_state,
    resolve_turn_runtime_flags,
)
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
    # TODO(!3473): skip LLM when companion_token_budget_allows_llm is false.
    """
    执行一轮完整对话。

    - 加载 context + prompt bundle + transcript
    - 组装 system prompt + messages
    - 调用 LLM（经 ``AgenticLoop`` + ``OutputQueue``）
    - 持久化 transcript

    返回 ``CompanionTurnResult``（``assistant_text`` 与可选 ``significance_perception``）。
    """
    store = deps.store
    llm_client = deps.llm_client
    transcript_compaction = deps.transcript_compaction
    transcript_llm_window_max_messages = deps.transcript_llm_window_max_messages
    repository_only_store_text = deps.repository_only_store_text
    runtime_context = deps.runtime_context
    incoming_bundle = runtime_context.implicit_signal_bundle
    resolved_time = resolve_client_time(
        store=store,
        incoming=(
            incoming_bundle.client_time if incoming_bundle is not None else None
        ),
        default_user_time_zone=(
            global_config_loaded_from_config_yaml.agent.companion_harness.default_user_time_zone
        ),
    )
    if resolved_time is not None:
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
        deps = replace(deps, runtime_context=runtime_context)
    preset_user_msg_uuid = deps.preset_user_msg_uuid
    langsmith_parent_run_enabled = deps.langsmith_parent_run_enabled
    tool_bg_idle_event = deps.tool_bg_idle_event
    agentic_output_queue = deps.agentic_output_queue
    user_message_batch = deps.user_message_batch
    input_batch = deps.input_batch
    assert agentic_output_queue is not None
    t0 = time.perf_counter()
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    implicit_signal_bundle = runtime_context.implicit_signal_bundle

    runtime_flags = resolve_turn_runtime_flags(
        track=track,
        user_text=user_text,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    user_text = runtime_flags.effective_user_text
    tick_proactive = runtime_flags.tick_proactive
    inner_tick_turn = runtime_flags.inner_tick_turn
    route_inner_activity = runtime_flags.route_inner_activity
    implicit_sign_on_turn = runtime_flags.implicit_sign_on_turn

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

    raw_idle_timeout = (
        os.environ.get("INTY_TOOL_BG_IDLE_WAIT_TIMEOUT_SEC", "").strip() or ""
    )
    try:
        idle_wait_timeout_sec = (
            float(raw_idle_timeout)
            if raw_idle_timeout
            else float(llm_client.config.async_chat_front_timeout_sec)
        )
    except ValueError:
        idle_wait_timeout_sec = float(
            llm_client.config.async_chat_front_timeout_sec
        )
    # TODO(tool-bg-idle-starves-user-chat): Maintenance often ends with tool_background still running; — #3123
    # the next turn waits on ``tool_bg_idle`` here while holding WS ``turn_lock``.
    # https://github.com/NascentCore/inty/issues/3123
    await _await_tool_background_idle_if_configured(
        tool_bg_idle_event,
        idle_wait_timeout_sec=idle_wait_timeout_sec,
        scope_registry_key=store.scope.registry_key(),
    )

    loaded_state = load_companion_turn_state(
        store=store,
        track=track,
        transcript_llm_window_max_messages=transcript_llm_window_max_messages,
    )
    if tick_proactive:
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
    context = loaded_state.context
    ts_user = utc_now()
    user_msg_uuid = (
        preset_user_msg_uuid if preset_user_msg_uuid else str(uuid.uuid4())
    )
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
    if (
        track
        in (
            CompanionTurnTrack.USER_CHAT,
            CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        )
        and user_message_batch is None
    ):
        # Fallback for direct (non-InputQueue) user chat so the AgenticLoop
        # branch below always has a batch; the App-WS caller delivers from the
        # turn result while the presence pump skips these rows.
        # TODO(#3543): user chat is user-initiated; replace the ``agent-initiated:``
        # batch-id prefix with an explicit direct-turn marker once pump-owned
        # delivery covers App-WS.
        user_message_batch = synthetic_user_message_batch(
            user_msg_uuid=user_msg_uuid,
            track_label=track.value,
        )
    prompt_plan = build_companion_turn_prompt_plan(
        store=store,
        loaded_state=loaded_state,
        tail_user_messages=tail_user_messages,
        track=track,
        tick_proactive=tick_proactive,
        implicit_sign_on_turn=implicit_sign_on_turn,
        runtime_context=runtime_context,
        transcript_compaction=transcript_compaction,
        tail_splice_thoughts=list(ai_private_splice_plan.thoughts),
    )
    tools_for_turn = prompt_plan.tools_for_turn
    messages = prompt_plan.messages
    trace_id = str(uuid.uuid4())
    langsmith_trace_acc = ""
    langsmith_llm_run_acc = ""

    last_text = ""
    skip_proactive_assistant_transcript_row = False
    significance_meta: dict[str, Any] | None = None
    turn_recall: str | None = None
    bootstrap_skip_final_transcript_assistant_row = False
    bootstrap_last_interim_assistant_msg_uuid: str | None = None
    in_turn_sync_persisted_transcript = False
    output_message_ids: tuple[str, ...] = ()
    t_loop = time.perf_counter()

    llm_runtime_bind_token: (
        contextvars.Token[LlmRuntimeEventBind | None] | None
    ) = None
    try:
        _llm_ev_phase = "inner_tick" if inner_tick_turn else "foreground_chat"
        llm_runtime_bind_token = companion_llm_runtime_event_bind_ctx.set(
            LlmRuntimeEventBind(
                memory_store=store,
                trace_id=trace_id,
                user_msg_uuid=user_msg_uuid,
                phase=_llm_ev_phase,
                scene=None,
            )
        )

        langsmith_slice = deps.langsmith_slice

        langsmith_parent_run = create_companion_turn_root_run(
            inty_trace_id=trace_id,
            user_msg_uuid=user_msg_uuid,
            chat_model=llm_client.resolve_model("chat"),
            tool_model=llm_client.resolve_model("tool"),
            user_id=context.user_id,
            companion_id=context.companion_id,
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
            langsmith_slice=langsmith_slice,
        )
        _ls_tid = companion_turn_langsmith_parent_trace_id_str(
            langsmith_parent_run
        )
        if _ls_tid:
            langsmith_trace_acc = _ls_tid
        if langsmith_parent_run is not None:
            logger.debug(
                "langsmith_companion_parent_run run_turn_bind inty_trace_id={} "
                "user_msg_uuid={} ls_trace_id={} defer_end_to_bg={}",
                trace_id,
                user_msg_uuid,
                _ls_tid,
                bool(tools_for_turn),
            )

        _langsmith_cm = nullcontext()
        if langsmith_parent_run is not None:
            from langsmith.run_helpers import tracing_context

            _langsmith_cm = tracing_context(parent=langsmith_parent_run)

        with _langsmith_cm:
            try:
                in_turn_sync_persisted_transcript = (
                    companion_turn_track_syncs_transcript_in_agentic_loop(track)
                )
                transcript_rel = (
                    paths.transcript
                    if track == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
                    else transcript_relative_path_for_turn_persistence(
                        track=track,
                    )
                )
                prepared = CompanionTurnLoopInput(
                    store=store,
                    llm_client=llm_client,
                    track=track,
                    runtime_flags=runtime_flags,
                    loaded_state=loaded_state,
                    prompt_plan=prompt_plan,
                    tail_user_messages=tail_user_messages,
                    messages=messages,
                    tools_for_turn=tools_for_turn,
                    trace_id=trace_id,
                    langsmith_slice=langsmith_slice,
                    runtime_context=runtime_context,
                    agentic_output_queue=agentic_output_queue,
                    user_message_batch=user_message_batch,
                    user_text=user_text,
                    ts_user=ts_user,
                    user_msg_uuid=user_msg_uuid,
                    ai_private_splice_plan=ai_private_splice_plan,
                    repository_only_store_text=repository_only_store_text,
                    langsmith_trace_id=langsmith_trace_acc,
                    langsmith_run_id=langsmith_llm_run_acc,
                    transcript_rel=transcript_rel,
                )
                plugin = resolve_agentic_loop(track=track)
                loop_out = await plugin.run(prepared)
                last_text = loop_out.assistant_text
                significance_meta = loop_out.significance_meta
                turn_recall = loop_out.turn_recall
                langsmith_trace_acc = loop_out.langsmith_trace_id
                langsmith_llm_run_acc = loop_out.langsmith_run_id
                bootstrap_skip_final_transcript_assistant_row = (
                    loop_out.skip_final_transcript_assistant_row
                )
                bootstrap_last_interim_assistant_msg_uuid = (
                    loop_out.last_interim_assistant_msg_uuid
                )
                output_message_ids = loop_out.output_message_ids
                if (
                    companion_turn_track_skips_empty_proactive_assistant_row(
                        track
                    )
                    and not last_text.strip()
                ):
                    skip_proactive_assistant_transcript_row = True
                logger.info(
                    "run_turn loop_done agentic_loop track={} loop_total_ms={:.0f}",
                    track.value,
                    (time.perf_counter() - t_loop) * 1000.0,
                )
            except BaseException as exc:
                end_companion_turn_root_run_safe(
                    langsmith_parent_run,
                    error=repr(exc),
                    ls_end_source="run_turn_sync_exc",
                )
                raise
            else:
                end_companion_turn_root_run_safe(
                    langsmith_parent_run, ls_end_source="run_turn_sync_ok"
                )
    finally:
        if llm_runtime_bind_token is not None:
            companion_llm_runtime_event_bind_ctx.reset(llm_runtime_bind_token)

    # 持久化 transcript
    # TODO(code-path-straightforwardness): refactor this function to accept — #3516
    # the transcript path (resolved at the time when turn track is determined) as an argument.
    rel_tr = (
        paths.transcript
        if implicit_sign_on_turn
        else transcript_relative_path_for_turn_persistence(
            track=track,
        )
    )
    assistant_msg_uuid = (
        bootstrap_last_interim_assistant_msg_uuid
        if bootstrap_last_interim_assistant_msg_uuid is not None
        else str(uuid.uuid4())
    )
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
    elif not in_turn_sync_persisted_transcript:
        append_turn_track_tail_user_transcript_rows(
            store,
            rel_tr,
            tail_user_messages=tail_user_messages,
            trace_id=trace_id,
            track=track,
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
            bootstrap_skip_final_transcript_assistant_row=(
                bootstrap_skip_final_transcript_assistant_row
            ),
        )
    )
    if (
        not bootstrap_skip_final_transcript_assistant_row
        and not skip_proactive_assistant_transcript_row
    ):
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

    logger.info(
        "run_turn done assistant_chars={} ms={:.0f} inty_trace_id={} user_msg_uuid={} "
        "langsmith_trace_id={} langsmith_run_id={}",
        len(last_text),
        (time.perf_counter() - t0) * 1000.0,
        trace_id,
        user_msg_uuid,
        langsmith_trace_acc or "",
        langsmith_llm_run_acc or "",
    )
    transcript_user_content = (
        USER_SIGNED_ON_TRIGGER_USER_TEXT
        if implicit_sign_on_turn
        else "\n".join(message.text for message in tail_user_messages)
    )
    return CompanionTurnResult(
        assistant_text=last_text,
        significance_perception=significance_meta,
        turn_recall=turn_recall,
        user_msg_uuid=user_msg_uuid,
        assistant_msg_uuid=assistant_msg_uuid,
        trace_id=trace_id,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_llm_run_acc,
        tool_background_started=False,
        assistant_source=runtime_flags.turn_type,
        inner_tick_activity=(
            route_inner_activity.value if inner_tick_turn else None
        ),
        turn_start_context_mode=context.context_mode,
        transcript_compaction=prompt_plan.transcript_compaction,
        transcript_user_content=transcript_user_content,
        output_message_ids=output_message_ids,
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
