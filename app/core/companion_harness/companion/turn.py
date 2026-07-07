"""Companion turn executor: 单轮对话的完整执行流程。

Memory-phase invariant **AwakeTurn**: see ``companion.turn_invariants`` — this module
only appends transcript JSONL on ``MemoryStore``; batch curation belongs in **DreamingBatch**.

可选 ``tool_bg_idle_event``：在加载 transcript 之前等待上一轮 tool_background 收尾，
保证主 ``transcript.jsonl``（或维护内在节拍用的 ``transcript_inner_tick.jsonl``）已含工具摘要后再组装本轮 chat/tool messages。

**Queue-serving turns**: Every track dispatches via ``AgenticLoop.run_track_turn`` with a
scope ``OutputQueue``. Settled ``USER_CHAT`` routes via ``user_turn.llm_loop_mode`` to
``SINGLE_LLM`` or ``DUAL_LLM`` mechanism; inner ticks and greeting use ``SINGLE_LLM``.

TODO(!3402): ``UserVisibleChunk`` + single ``UserVisibleChunkSink``; retire non-queue ``bootstrap_interim_output_sink``.
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
    expand_manifest_rows,
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
from app.core.companion_harness.prompt_builder import (
    PromptBuilder,
    prompt_messages_to_openai_dicts,
    refresh_single_llm_bootstrap_chat_prompt_prefix,
    refresh_single_llm_user_chat_prompt_prefix,
)
from app.core.companion_harness.loop.agentic_loop import AgenticLoop
from app.core.companion_harness.loop.config import (
    AgenticLoopMechanism,
    UserTurnLlmLoopMode,
    resolved_user_turn_batch_messages_llm_call_mode,
    resolved_user_turn_llm_loop_mode,
)
from app.core.companion_harness.agentic_companion.types import (
    synthetic_user_message_batch,
)
from app.core.companion_harness.loop.context import (
    build_bootstrap_user_chat_loop_context,
    build_implicit_sign_on_greeting_loop_context,
    build_inner_tick_chat_only_loop_context,
    build_inner_tick_tool_loop_context,
    build_settled_dual_llm_user_chat_loop_context,
    build_settled_user_chat_loop_context,
    prompt_plan_from_openai_messages,
)
from .dual_llm_message_stacks import (
    dual_llm_system_message_variants,
    replace_leading_system_messages_multi,
)
from .turn_deps import CompanionTurnDeps
from .turn_track import turn_flags_for_track
from .turn_pipeline import (
    build_companion_turn_prompt_plan,
    load_companion_turn_state,
    resolve_turn_runtime_flags,
)
from .turn_tail_user import (
    append_tail_user_transcript_rows,
    resolve_turn_tail_user_messages,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
)
from .turn_routes import (
    TurnRouteMode,
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


def _memory_store_write_allowlist_for_track(
    track: CompanionTurnTrack,
) -> frozenset[str]:
    match track:
        case CompanionTurnTrack.INNER_TICK_AUTONOMY:
            return MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY
        case CompanionTurnTrack.INNER_TICK_MONOLOG:
            return frozenset()
        case _:
            return MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST


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
    inner_tick_turn, route_inner_activity = turn_flags_for_track(track)
    implicit_signal_bundle = runtime_context.implicit_signal_bundle

    runtime_flags = resolve_turn_runtime_flags(
        track=track,
        user_text=user_text,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    user_text = runtime_flags.effective_user_text
    tick_proactive = runtime_flags.tick_proactive
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
        inner_tick_turn=inner_tick_turn,
        route_inner_activity=route_inner_activity,
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
    bundle = loaded_state.bundle
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
    route_mode = prompt_plan.route_mode
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
                "user_msg_uuid={} ls_trace_id={} route_mode={} defer_end_to_bg={}",
                trace_id,
                user_msg_uuid,
                _ls_tid,
                route_mode.value,
                route_mode
                == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL,
            )

        _langsmith_cm = nullcontext()
        if langsmith_parent_run is not None:
            from langsmith.run_helpers import tracing_context

            _langsmith_cm = tracing_context(parent=langsmith_parent_run)

        with _langsmith_cm:
            try:
                if (
                    track
                    in (
                        CompanionTurnTrack.USER_CHAT,
                        CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
                    )
                    and user_message_batch is not None
                ):
                    in_turn_sync_persisted_transcript = True
                    rel_tr_agentic_loop = (
                        transcript_relative_path_for_turn_persistence(
                            inner_tick_turn=False,
                            inner_tick_activity=route_inner_activity,
                        )
                    )

                    async def _bootstrap_single_llm_after_tool_round(
                        messages_with_tool_results: list[dict[str, Any]],
                    ) -> list[dict[str, Any]]:
                        return refresh_single_llm_bootstrap_chat_prompt_prefix(
                            store=store,
                            messages=messages_with_tool_results,
                            runtime_context=runtime_context,
                        )

                    async def _settled_single_llm_after_tool_round(
                        messages_with_tool_results: list[dict[str, Any]],
                    ) -> list[dict[str, Any]]:
                        return refresh_single_llm_user_chat_prompt_prefix(
                            store=store,
                            messages=messages_with_tool_results,
                            runtime_context=runtime_context,
                        )

                    # TODO(!3460): Move dual-LLM message-stack assembly into loop/context.py.
                    llm_loop_mode = resolved_user_turn_llm_loop_mode()
                    agentic_loop = AgenticLoop(
                        store=store,
                        llm_client=llm_client.async_llm_client,
                        legacy_llm_client=llm_client,
                    )
                    if track == CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
                        transcript_window = loaded_state.transcript_window
                        if track_uses_ai_private_splice(track):
                            transcript_window = expand_manifest_rows(
                                store,
                                loaded_state.transcript_window,
                            )
                        bootstrap_prompt_plan = PromptBuilder(
                            bundle=bundle,
                            context=context,
                            runtime_context=runtime_context,
                        ).build_bootstrap_user_chat_prompt(
                            transcript_window=transcript_window,
                            tail_user_messages=tail_user_messages,
                            tools=tuple(tools_for_turn),
                            implicit_sign_on_turn=implicit_sign_on_turn,
                            tail_splice_thoughts=ai_private_splice_plan.thoughts,
                        )
                        loop_context = build_bootstrap_user_chat_loop_context(
                            messages=messages,
                            tools_for_turn=tools_for_turn,
                            repository_only_store_text=repository_only_store_text,
                            trace_id=trace_id,
                            user_text=user_text,
                            ts_user=ts_user,
                            user_msg_uuid=user_msg_uuid,
                            transcript_rel=rel_tr_agentic_loop,
                            langsmith_slice=langsmith_slice,
                            runtime_context=runtime_context,
                            stack_depth=sum(
                                1
                                for message in bootstrap_prompt_plan.messages
                                if message.role.value == "system"
                            ),
                            langsmith_trace_id=langsmith_trace_acc,
                            langsmith_run_id=langsmith_llm_run_acc,
                            after_tool_messages_appended=_bootstrap_single_llm_after_tool_round,
                            output_queue=agentic_output_queue,
                            user_message_batch=user_message_batch,
                            tail_user_messages=tail_user_messages,
                            prompt_plan=bootstrap_prompt_plan,
                        )
                        loop_out = await agentic_loop.run_track_turn(
                            mechanism=AgenticLoopMechanism.SINGLE_LLM,
                            context=loop_context,
                        )
                    elif (
                        llm_loop_mode == UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM
                    ):
                        transcript_window = loaded_state.transcript_window
                        if track_uses_ai_private_splice(track):
                            transcript_window = expand_manifest_rows(
                                store,
                                loaded_state.transcript_window,
                            )
                        single_llm_prompt_plan = PromptBuilder(
                            bundle=bundle,
                            context=context,
                            runtime_context=runtime_context,
                        ).build_user_chat_prompt(
                            transcript_window=transcript_window,
                            tail_user_messages=tail_user_messages,
                            tools=tuple(tools_for_turn),
                            implicit_sign_on_turn=implicit_sign_on_turn,
                            tail_splice_thoughts=ai_private_splice_plan.thoughts,
                        )
                        loop_context = build_settled_user_chat_loop_context(
                            messages=messages,
                            tools_for_turn=tools_for_turn,
                            repository_only_store_text=repository_only_store_text,
                            trace_id=trace_id,
                            user_text=user_text,
                            ts_user=ts_user,
                            user_msg_uuid=user_msg_uuid,
                            transcript_rel=rel_tr_agentic_loop,
                            langsmith_slice=langsmith_slice,
                            runtime_context=runtime_context,
                            stack_depth=sum(
                                1
                                for message in single_llm_prompt_plan.messages
                                if message.role.value == "system"
                            ),
                            langsmith_trace_id=langsmith_trace_acc,
                            langsmith_run_id=langsmith_llm_run_acc,
                            after_tool_messages_appended=_settled_single_llm_after_tool_round,
                            output_queue=agentic_output_queue,
                            user_message_batch=user_message_batch,
                            tail_user_messages=tail_user_messages,
                            prompt_plan=single_llm_prompt_plan,
                        )
                        loop_out = await agentic_loop.run_track_turn(
                            mechanism=AgenticLoopMechanism.SINGLE_LLM,
                            context=loop_context,
                        )
                    else:
                        _, chat_system_msgs = dual_llm_system_message_variants(
                            store=store,
                            bundle=bundle,
                            context=context,
                            inner_tick_turn=False,
                            route_inner_activity=route_inner_activity,
                            runtime_context=runtime_context,
                        )
                        _stack_depth = len(prompt_plan.system_messages)
                        chat_msgs = replace_leading_system_messages_multi(
                            messages,
                            chat_system_msgs,
                            stack_depth=_stack_depth,
                        )
                        dual_llm_prompt_builder = PromptBuilder(
                            bundle=bundle,
                            context=context,
                            runtime_context=runtime_context,
                        )
                        tool_plan = dual_llm_prompt_builder.build_settled_user_chat_dual_llm_tool_prompt_plan(
                            base_messages=messages,
                            stack_depth=_stack_depth,
                            tools=tuple(tools_for_turn),
                        )
                        tool_msgs = prompt_messages_to_openai_dicts(
                            tool_plan.messages
                        )
                        loop_context = build_settled_dual_llm_user_chat_loop_context(
                            messages=messages,
                            tools_for_turn=tools_for_turn,
                            repository_only_store_text=repository_only_store_text,
                            trace_id=trace_id,
                            user_text=user_text,
                            ts_user=ts_user,
                            user_msg_uuid=user_msg_uuid,
                            transcript_rel=rel_tr_agentic_loop,
                            langsmith_slice=langsmith_slice,
                            runtime_context=runtime_context,
                            stack_depth=_stack_depth,
                            langsmith_trace_id=langsmith_trace_acc,
                            langsmith_run_id=langsmith_llm_run_acc,
                            output_queue=agentic_output_queue,
                            user_message_batch=user_message_batch,
                            tail_user_messages=tail_user_messages,
                            dual_llm_chat_msgs=tuple(chat_msgs),
                            dual_llm_tool_msgs=tuple(tool_msgs),
                            prompt_bundle=bundle,
                            context_meta=context,
                        )
                        loop_out = await agentic_loop.run_track_turn(
                            mechanism=AgenticLoopMechanism.DUAL_LLM,
                            context=loop_context,
                        )
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
                    logger.info(
                        "run_turn loop_done agentic_loop track={} loop_total_ms={:.0f}",
                        track.value,
                        (time.perf_counter() - t_loop) * 1000.0,
                    )
                elif track == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
                    greeting_batch = user_message_batch
                    if greeting_batch is None:
                        greeting_batch = synthetic_user_message_batch(
                            user_msg_uuid=user_msg_uuid,
                            track_label=track.value,
                        )
                    rel_tr_greeting = paths.transcript
                    greeting_prompt_plan = prompt_plan_from_openai_messages(
                        messages,
                        tools=(),
                    )
                    agentic_loop = AgenticLoop(
                        store=store,
                        llm_client=llm_client.async_llm_client,
                        legacy_llm_client=llm_client,
                    )
                    loop_context = build_implicit_sign_on_greeting_loop_context(
                        messages=messages,
                        repository_only_store_text=repository_only_store_text,
                        trace_id=trace_id,
                        user_text=user_text,
                        ts_user=ts_user,
                        user_msg_uuid=user_msg_uuid,
                        transcript_rel=rel_tr_greeting,
                        langsmith_slice=langsmith_slice,
                        runtime_context=runtime_context,
                        stack_depth=sum(
                            1
                            for message in messages
                            if message.get("role") == "system"
                        ),
                        langsmith_trace_id=langsmith_trace_acc,
                        langsmith_run_id=langsmith_llm_run_acc,
                        output_queue=agentic_output_queue,
                        user_message_batch=greeting_batch,
                        tail_user_messages=tail_user_messages,
                        prompt_plan=greeting_prompt_plan,
                    )
                    loop_out = await agentic_loop.run_track_turn(
                        mechanism=AgenticLoopMechanism.SINGLE_LLM,
                        context=loop_context,
                    )
                    last_text = loop_out.assistant_text
                    significance_meta = loop_out.significance_meta
                    turn_recall = loop_out.turn_recall
                    langsmith_trace_acc = loop_out.langsmith_trace_id
                    langsmith_llm_run_acc = loop_out.langsmith_run_id
                    bootstrap_skip_final_transcript_assistant_row = (
                        loop_out.skip_final_transcript_assistant_row
                    )
                    output_message_ids = loop_out.output_message_ids
                    logger.info(
                        "run_turn loop_done agentic_loop greeting loop_total_ms={:.0f}",
                        (time.perf_counter() - t_loop) * 1000.0,
                    )
                elif track in (
                    CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
                    CompanionTurnTrack.INNER_TICK_SCHEDULED,
                ):
                    in_turn_sync_persisted_transcript = True
                    inner_batch = user_message_batch
                    if inner_batch is None:
                        inner_batch = synthetic_user_message_batch(
                            user_msg_uuid=user_msg_uuid,
                            track_label=track.value,
                        )
                    rel_tr_inner = (
                        transcript_relative_path_for_turn_persistence(
                            inner_tick_turn=True,
                            inner_tick_activity=route_inner_activity,
                        )
                    )
                    inner_prompt_plan = prompt_plan_from_openai_messages(
                        messages,
                        tools=(),
                    )
                    agentic_loop = AgenticLoop(
                        store=store,
                        llm_client=llm_client.async_llm_client,
                        legacy_llm_client=llm_client,
                    )
                    loop_context = build_inner_tick_chat_only_loop_context(
                        track=track,
                        messages=messages,
                        repository_only_store_text=repository_only_store_text,
                        trace_id=trace_id,
                        user_text=user_text,
                        ts_user=ts_user,
                        user_msg_uuid=user_msg_uuid,
                        transcript_rel=rel_tr_inner,
                        langsmith_slice=langsmith_slice,
                        runtime_context=runtime_context,
                        stack_depth=sum(
                            1
                            for message in messages
                            if message.get("role") == "system"
                        ),
                        langsmith_trace_id=langsmith_trace_acc,
                        langsmith_run_id=langsmith_llm_run_acc,
                        output_queue=agentic_output_queue,
                        user_message_batch=inner_batch,
                        tail_user_messages=tail_user_messages,
                        prompt_plan=inner_prompt_plan,
                        route_inner_activity=route_inner_activity,
                    )
                    loop_out = await agentic_loop.run_track_turn(
                        mechanism=AgenticLoopMechanism.SINGLE_LLM,
                        context=loop_context,
                    )
                    last_text = loop_out.assistant_text
                    langsmith_trace_acc = loop_out.langsmith_trace_id
                    langsmith_llm_run_acc = loop_out.langsmith_run_id
                    bootstrap_skip_final_transcript_assistant_row = (
                        loop_out.skip_final_transcript_assistant_row
                    )
                    # Proactive envelope may silence the turn (output_to_user=false)
                    # on both PROACTIVE_CHAT and SCHEDULED; no empty assistant row.
                    if not last_text.strip():
                        skip_proactive_assistant_transcript_row = True
                    output_message_ids = loop_out.output_message_ids
                    logger.info(
                        "run_turn loop_done agentic_loop inner_tick_chat track={} loop_total_ms={:.0f}",
                        track.value,
                        (time.perf_counter() - t_loop) * 1000.0,
                    )
                elif track in (
                    CompanionTurnTrack.INNER_TICK_MONOLOG,
                    CompanionTurnTrack.INNER_TICK_AUTONOMY,
                ):
                    in_turn_sync_persisted_transcript = True
                    throttle_batch = user_message_batch
                    if throttle_batch is None:
                        throttle_batch = synthetic_user_message_batch(
                            user_msg_uuid=user_msg_uuid,
                            track_label=track.value,
                        )
                    rel_tr_throttle = (
                        transcript_relative_path_for_turn_persistence(
                            inner_tick_turn=True,
                            inner_tick_activity=route_inner_activity,
                        )
                    )
                    throttle_prompt_plan = prompt_plan_from_openai_messages(
                        messages,
                        tools=tuple(tools_for_turn),
                    )
                    agentic_loop = AgenticLoop(
                        store=store,
                        llm_client=llm_client.async_llm_client,
                        legacy_llm_client=llm_client,
                    )
                    loop_context = build_inner_tick_tool_loop_context(
                        track=track,
                        messages=messages,
                        tools_for_turn=tools_for_turn,
                        write_allowlist=_memory_store_write_allowlist_for_track(
                            track
                        ),
                        repository_only_store_text=repository_only_store_text,
                        trace_id=trace_id,
                        user_text=user_text,
                        ts_user=ts_user,
                        user_msg_uuid=user_msg_uuid,
                        transcript_rel=rel_tr_throttle,
                        langsmith_slice=langsmith_slice,
                        runtime_context=runtime_context,
                        stack_depth=sum(
                            1
                            for message in messages
                            if message.get("role") == "system"
                        ),
                        langsmith_trace_id=langsmith_trace_acc,
                        langsmith_run_id=langsmith_llm_run_acc,
                        output_queue=agentic_output_queue,
                        user_message_batch=throttle_batch,
                        tail_user_messages=tail_user_messages,
                        prompt_plan=throttle_prompt_plan,
                        route_inner_activity=route_inner_activity,
                    )
                    loop_out = await agentic_loop.run_track_turn(
                        mechanism=AgenticLoopMechanism.SINGLE_LLM,
                        context=loop_context,
                    )
                    last_text = loop_out.assistant_text
                    langsmith_trace_acc = loop_out.langsmith_trace_id
                    langsmith_llm_run_acc = loop_out.langsmith_run_id
                    bootstrap_skip_final_transcript_assistant_row = (
                        loop_out.skip_final_transcript_assistant_row
                    )
                    output_message_ids = loop_out.output_message_ids
                    logger.info(
                        "run_turn loop_done agentic_loop inner_tick_tool track={} loop_total_ms={:.0f}",
                        track.value,
                        (time.perf_counter() - t_loop) * 1000.0,
                    )
                else:
                    raise RuntimeError(
                        f"unhandled turn track={track.value} route_mode={route_mode.value}; "
                        "all tracks must run via AgenticLoop + OutputQueue"
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
            inner_tick_turn=inner_tick_turn,
            inner_tick_activity=route_inner_activity,
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
        needs_turn_track_user_row_metadata = (
            inner_tick_turn
            or tick_proactive
            or track == CompanionTurnTrack.INNER_TICK_SCHEDULED
        )
        if (
            len(tail_user_messages) > 1
            or not needs_turn_track_user_row_metadata
        ):
            append_tail_user_transcript_rows(
                store,
                rel_tr,
                tail_user_messages=tail_user_messages,
                trace_id=trace_id,
            )
        else:
            user_row: dict[str, Any] = {
                "role": "user",
                "content": tail_user_messages[0].text,
                "ts": tail_user_messages[0].received_at_utc.isoformat(),
                "uuid": tail_user_messages[0].message_id,
            }
            if inner_tick_turn:
                user_row["inner_tick"] = True
            if tick_proactive:
                # TODO(#3401): use enum for message type, not bool proactive_chat
                user_row["proactive_chat"] = True
            if track == CompanionTurnTrack.INNER_TICK_SCHEDULED:
                user_row["scheduled"] = True
            user_row["trace_id"] = trace_id
            store.append_jsonl_record(rel_tr, user_row)
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
