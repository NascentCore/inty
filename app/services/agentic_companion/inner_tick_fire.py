"""Inner-tick glue: presence coordinator guards, harness runtime, channel delivery.

Orchestrates ``companion_harness.runtime.inner_tick_fire`` (kernel due + turn),
``inner_tick_scope`` (ORM), and ``inner_tick_deliver`` (chat_history + WS/IM).
WS wire envelopes and Weixin plain text share this path.

Locking: each ``try_fire_*`` acquires **scope** ``CompanionSession.turn_lock`` (#3272).
User chat on the same scope also holds that lock — inner ticks (including dreaming) and
user messages serialize per ``(user_id, agent_id, chat_id)``. Prototype: single presence
per paired user (``companion_harness`` AGENTS.md).

TODO(!3516): Simplify scope serialization and foreground-pending skip rules during
the AgenticLoop + InputQueue/OutputQueue + Channel overhaul.

TODO(dreaming-cluster-lock): Multi-process backend needs Postgres advisory lock around
dreaming batches — https://github.com/NascentCore/inty/issues/3271

Prototype: inner-tick fire paths do not call ``subscription_service`` (no
``check_chat_limit`` / ``record_usage``). User chat billing stays in ``chat_ws.py``.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from loguru import logger

from app.core.companion_harness.companion.dreaming_observability import (
    DreamingBatchOutcome,
)
from app.core.companion_harness.companion.inner_tick_kind import InnerTickKind
from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.models import (
    InnerTickThrottleKind,
    MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.runtime.inner_tick_fire import (
    InnerTickKernelInput,
    InnerTickThrottleSnapshot,
    due_scheduled_task,
    inner_tick_remain_seconds,
    kernel_fire_proactive,
    kernel_fire_scheduled,
    kernel_fire_throttled,
    proactive_chat_remain_seconds,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.chat_websocket import (
    build_inner_tick_wire_meta,
    dump_chat_ws_companion_wire_meta,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services import chat_history_service, companion_chat_service
from app.services.chat_service import generate_session_id
from app.services.agentic_companion.inner_tick_deliver import (
    InnerTickVisibleDeliverInput,
    deliver_visible_inner_tick_turn,
)
from app.services.agentic_companion.inner_tick_kernel_context import (
    build_inner_tick_kernel_context,
)
from app.services.agentic_companion.inner_tick_scope import (
    InnerTickFireInput,
    InnerTickModelSource,
    InnerTickScopeCoords,
    resolve_inner_tick_scope_coords,
)
from app.services.agentic_companion.inner_tick_turn_scope import (
    inner_tick_turn_scope,
)
from app.services.agentic_companion.ws_implicit_signals import (
    implicit_signal_bundle_from_tc_box,
)


def _throttle_snapshot(
    fire_input: InnerTickFireInput,
) -> InnerTickThrottleSnapshot:
    coordinator = fire_input.coordinator
    return InnerTickThrottleSnapshot(
        last_monolog_monotonic=coordinator.last_monolog_inner_tick_monotonic(),
        last_monolog_line_count=coordinator.last_monolog_transcript_line_count(),
        last_autonomy_monotonic=coordinator.last_autonomy_inner_tick_monotonic(),
        last_autonomy_line_count=coordinator.last_autonomy_transcript_line_count(),
    )


def _stub_request(
    *,
    user_text: str,
    preset_uid: str,
    implicit: ImplicitSignalBundle | None,
) -> ChatCompletionRequest:
    stub_utc = implicit.client_time if implicit else None
    return ChatCompletionRequest(
        messages=[ChatMessage(role="user", content=user_text)],
        message_id=preset_uid,
        user_time_context=stub_utc,
    )


async def _kernel_context(
    coords: InnerTickScopeCoords,
    fire_input: InnerTickFireInput,
    *,
    preset_uid: str,
    background_output_sink,
) -> tuple[InnerTickKernelInput, CompanionSession] | None:
    ws_implicit = implicit_signal_bundle_from_tc_box(fire_input.tc_box)
    return await build_inner_tick_kernel_context(
        user_id=coords.user_id,
        agent_id=coords.agent_id,
        chat_row_id=coords.chat_row_id,
        model_override=coords.model_override,
        throttle=_throttle_snapshot(fire_input),
        runtime_context=TurnRuntimeContext(
            channel=fire_input.delivery.runtime_channel,
            implicit_signal_bundle=ws_implicit,
        ),
        preset_uid=preset_uid,
        background_output_sink=background_output_sink,
    )


async def try_fire_scheduled_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    # TODO(#3473): gate proactive + scheduled fire on token budget before turn_lock.
    # TODO(scheduled-presence-independent): sole caller is presence-bound
    # ``run_inner_tick_poll``; refactor so due tasks fire from scope worker — #3689
    """When ``schedule_queue`` has a due pending task, run one inner-tick reminder turn."""
    coords = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    if coords is None:
        return False

    preset_uid = str(uuid.uuid4())
    ctx_pair = await _kernel_context(
        coords, fire_input, preset_uid=preset_uid, background_output_sink=None
    )
    if ctx_pair is None:
        return False
    kernel_input, scope_session = ctx_pair

    due_task = due_scheduled_task(kernel_input.mem_store)
    if due_task is None:
        return False

    coordinator = fire_input.coordinator
    ws_conn_id = fire_input.ws_conn_id
    session_id = generate_session_id(str(coords.chat_row_id))

    async with inner_tick_turn_scope(session=scope_session):
        if coordinator.inner_tick_monolog_foreground_pending():
            logger.debug(
                "companion_ws_scheduled_reminder skipped prev_monolog_pending "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                coords.user_id,
                coords.agent_id,
            )
            return False
        coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
        if coordinator.inner_tick_proactive_tool_bg_still_running():
            logger.debug(
                "companion_ws_scheduled_reminder skipped prev_inner_tick_tool_bg "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                coords.user_id,
                coords.agent_id,
            )
            return False

        kernel_result = await kernel_fire_scheduled(kernel_input, due_task)
        if kernel_result is None:
            logger.warning(
                "companion_ws_scheduled_reminder empty reply ws_conn_id={} user={} "
                "agent={} task_id={}",
                ws_conn_id,
                coords.user_id,
                coords.agent_id,
                due_task.id,
            )
            return True

        companion_turn = kernel_result.turn
        if companion_turn.tool_background_started:
            coordinator.bind_inner_tick_proactive_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=coords.user_id,
                    agent_id=coords.agent_id,
                    chat_id=coords.chat_row_id,
                    resolved_chat_model=coords.model_override,
                )
            )
        else:
            coordinator.bind_inner_tick_proactive_tool_bg_idle(None)

        ws_implicit = implicit_signal_bundle_from_tc_box(fire_input.tc_box)
        delivered = await deliver_visible_inner_tick_turn(
            InnerTickVisibleDeliverInput(
                delivery=fire_input.delivery,
                session_id=session_id,
                agent_id=coords.agent_id,
                chat_row_agent_id=coords.chat_row_agent_id,
                ws_conn_id=ws_conn_id,
                preset_uid=preset_uid,
                transcript_user_text=kernel_result.transcript_user_text,
                companion_turn=companion_turn,
                stub_request=_stub_request(
                    user_text=kernel_result.transcript_user_text,
                    preset_uid=preset_uid,
                    implicit=ws_implicit,
                ),
                user_wire_meta=build_inner_tick_wire_meta(
                    InnerTickKind.SCHEDULED,
                    scheduled_task_id=due_task.id,
                ),
                companion_scheduled_reminder=True,
                scheduled_task_id=due_task.id,
                log_label="companion_ws_scheduled_reminder",
                skip_user_history=False,
            )
        )

    if delivered:
        logger.info(
            "companion_ws_scheduled_reminder pushed assistant ws_conn_id={} user={} "
            "agent={} chat_id={} task_id={}",
            ws_conn_id,
            coords.user_id,
            coords.agent_id,
            coords.chat_row_id,
            due_task.id,
        )
    else:
        logger.info(
            "companion_ws_scheduled_reminder silent ws_conn_id={} user={} agent={} "
            "chat_id={} task_id={}",
            ws_conn_id,
            coords.user_id,
            coords.agent_id,
            coords.chat_row_id,
            due_task.id,
        )
    return True


async def try_fire_proactive_chat_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """If companion transcript says proactive chat is due, run one turn and queue WS payload."""
    coords = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    if coords is None:
        return False

    preset_uid = str(uuid.uuid4())
    ctx_pair = await _kernel_context(
        coords, fire_input, preset_uid=preset_uid, background_output_sink=None
    )
    if ctx_pair is None:
        return False
    kernel_input, scope_session = ctx_pair

    if proactive_chat_remain_seconds(kernel_input.mem_store) > 0:
        return False

    coordinator = fire_input.coordinator
    ws_conn_id = fire_input.ws_conn_id
    session_id = generate_session_id(str(coords.chat_row_id))

    async with inner_tick_turn_scope(session=scope_session):
        coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
        if coordinator.inner_tick_proactive_tool_bg_still_running():
            logger.debug(
                "companion_ws_proactive_chat skipped prev_inner_tick_tool_bg "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                coords.user_id,
                coords.agent_id,
            )
            return False

        kernel_result = await kernel_fire_proactive(kernel_input)
        companion_turn = kernel_result.turn
        if companion_turn.tool_background_started:
            coordinator.bind_inner_tick_proactive_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=coords.user_id,
                    agent_id=coords.agent_id,
                    chat_id=coords.chat_row_id,
                    resolved_chat_model=coords.model_override,
                )
            )
        else:
            coordinator.bind_inner_tick_proactive_tool_bg_idle(None)

        ws_implicit = implicit_signal_bundle_from_tc_box(fire_input.tc_box)
        delivered = await deliver_visible_inner_tick_turn(
            InnerTickVisibleDeliverInput(
                delivery=fire_input.delivery,
                session_id=session_id,
                agent_id=coords.agent_id,
                chat_row_agent_id=coords.chat_row_agent_id,
                ws_conn_id=ws_conn_id,
                preset_uid=preset_uid,
                transcript_user_text=kernel_result.transcript_user_text,
                companion_turn=companion_turn,
                stub_request=_stub_request(
                    user_text=kernel_result.transcript_user_text,
                    preset_uid=preset_uid,
                    implicit=ws_implicit,
                ),
                user_wire_meta=build_inner_tick_wire_meta(
                    InnerTickKind.PROACTIVE_CHAT,
                ),
                companion_scheduled_reminder=None,
                scheduled_task_id=None,
                log_label="companion_ws_proactive_chat",
                skip_user_history=False,
            )
        )

    if delivered:
        logger.info(
            "companion_ws_proactive_chat pushed assistant ws_conn_id={} user={} agent={} "
            "chat_id={}",
            ws_conn_id,
            coords.user_id,
            coords.agent_id,
            coords.chat_row_id,
        )
    else:
        logger.info(
            "companion_ws_proactive_chat silent ws_conn_id={} user={} agent={} chat_id={}",
            ws_conn_id,
            coords.user_id,
            coords.agent_id,
            coords.chat_row_id,
        )
    return True


async def try_fire_autonomy_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """AUTONOMY inner-tick: silent self-directed turn during user idle."""
    coords = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    if coords is None:
        return False

    preset_uid = str(uuid.uuid4())
    ctx_pair = await _kernel_context(
        coords,
        fire_input,
        preset_uid=preset_uid,
        background_output_sink=fire_input.coordinator.background_sink,
    )
    if ctx_pair is None:
        return False
    kernel_input, scope_session = ctx_pair

    if (
        inner_tick_remain_seconds(
            InnerTickKind.AUTONOMY,
            kernel_input.mem_store,
            kernel_input.throttle,
        )
        > 0
    ):
        return False

    coordinator = fire_input.coordinator
    ws_conn_id = fire_input.ws_conn_id
    ws_implicit = implicit_signal_bundle_from_tc_box(fire_input.tc_box)
    autonomy_runtime = TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=ws_implicit,
    )
    kernel_input = InnerTickKernelInput(
        manager=kernel_input.manager,
        session=kernel_input.session,
        mem_store=kernel_input.mem_store,
        throttle=kernel_input.throttle,
        runtime_context=autonomy_runtime,
        preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
        background_output_sink=kernel_input.background_output_sink,
    )

    async with inner_tick_turn_scope(session=scope_session):
        coordinator.clear_inner_tick_autonomy_tool_bg_idle_if_idle()
        if coordinator.inner_tick_autonomy_tool_bg_still_running():
            logger.debug(
                "companion_ws_autonomy_inner_tick skipped prev_autonomy_tool_bg "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                coords.user_id,
                coords.agent_id,
            )
            return False
        try:
            kernel_result = await kernel_fire_throttled(
                InnerTickKind.AUTONOMY,
                kernel_input,
            )
        except Exception as exc:
            logger.warning(
                "companion_ws_autonomy_inner_tick run_turn failed ws_conn_id={} "
                "user={} agent={}: {}",
                ws_conn_id,
                coords.user_id,
                coords.agent_id,
                exc,
            )
            raise

        companion_turn = kernel_result.turn
        if companion_turn.tool_background_started:
            coordinator.bind_inner_tick_autonomy_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=coords.user_id,
                    agent_id=coords.agent_id,
                    chat_id=coords.chat_row_id,
                    resolved_chat_model=coords.model_override,
                )
            )
        else:
            coordinator.bind_inner_tick_autonomy_tool_bg_idle(None)

        if (
            kernel_result.throttle_kind == InnerTickThrottleKind.AUTONOMY
            and kernel_result.throttle_line_count is not None
        ):
            coordinator.mark_autonomy_inner_tick_fired(
                time.monotonic(),
                kernel_result.throttle_line_count,
            )

    logger.info(
        "companion_ws_autonomy_inner_tick fired ws_conn_id={} user={} agent={} "
        "chat_id={} tool_background_started={}",
        ws_conn_id,
        coords.user_id,
        coords.agent_id,
        coords.chat_row_id,
        companion_turn.tool_background_started,
    )
    return True


async def try_fire_monolog_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """If companion transcript says monolog inner-tick is due, run one MONOLOG turn."""
    coords = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    if coords is None:
        return False

    preset_uid = str(uuid.uuid4())
    ctx_pair = await _kernel_context(
        coords,
        fire_input,
        preset_uid=preset_uid,
        background_output_sink=fire_input.coordinator.background_sink,
    )
    if ctx_pair is None:
        return False
    kernel_input, scope_session = ctx_pair

    if (
        inner_tick_remain_seconds(
            InnerTickKind.MONOLOG,
            kernel_input.mem_store,
            kernel_input.throttle,
        )
        > 0
    ):
        return False

    coordinator = fire_input.coordinator
    ws_conn_id = fire_input.ws_conn_id
    session_id = generate_session_id(str(coords.chat_row_id))
    ws_implicit = implicit_signal_bundle_from_tc_box(fire_input.tc_box)
    stub_request = _stub_request(
        user_text=MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER,
        preset_uid=preset_uid,
        implicit=ws_implicit,
    )

    async with inner_tick_turn_scope(session=scope_session):
        if coordinator.inner_tick_monolog_foreground_pending():
            logger.debug(
                "companion_ws_monolog_inner_tick skipped prev_inner_tick_pending "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                coords.user_id,
                coords.agent_id,
            )
            return False

        coordinator.set_foreground_pending(
            preset_uid,
            {
                "session_id": session_id,
                "agent_id": coords.agent_id,
                "user_id": coords.user_id,
                "chat_id": coords.chat_row_id,
                "request": stub_request,
                "effective_local_id": None,
                "ws_inner_tick_monolog": True,
            },
        )
        try:
            kernel_result = await kernel_fire_throttled(
                InnerTickKind.MONOLOG,
                kernel_input,
            )
        except Exception as exc:
            if not getattr(exc, "companion_tool_background_started", False):
                coordinator.remove_foreground_pending(preset_uid)
            raise

        companion_turn = kernel_result.turn
        reply_stripped = str(companion_turn.assistant_text or "").strip()
        if not companion_turn.tool_background_started:
            coordinator.remove_foreground_pending(preset_uid)

        user_meta = build_inner_tick_wire_meta(InnerTickKind.MONOLOG)
        user_row_id = await chat_history_service.add_user_message_async(
            session_id,
            MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER,
            meta_data=dump_chat_ws_companion_wire_meta(user_meta),
        )

        if (
            companion_turn.tool_background_started
            and coordinator.has_foreground_pending(preset_uid)
        ):
            coordinator.update_foreground_pending(
                preset_uid,
                {"foreground_user_message_id": user_row_id},
            )

        if reply_stripped:
            await deliver_visible_inner_tick_turn(
                InnerTickVisibleDeliverInput(
                    delivery=fire_input.delivery,
                    session_id=session_id,
                    agent_id=coords.agent_id,
                    chat_row_agent_id=coords.chat_row_agent_id,
                    ws_conn_id=ws_conn_id,
                    preset_uid=preset_uid,
                    transcript_user_text=kernel_result.transcript_user_text,
                    companion_turn=companion_turn,
                    stub_request=stub_request,
                    user_wire_meta=user_meta,
                    companion_scheduled_reminder=None,
                    scheduled_task_id=None,
                    log_label="companion_ws_monolog_inner_tick",
                    skip_user_history=True,
                )
            )

        if (
            kernel_result.throttle_kind == InnerTickThrottleKind.MONOLOG
            and kernel_result.throttle_line_count is not None
        ):
            coordinator.mark_monolog_inner_tick_fired(
                time.monotonic(),
                kernel_result.throttle_line_count,
            )

    if reply_stripped:
        logger.info(
            "companion_ws_monolog_inner_tick pushed assistant ws_conn_id={} "
            "user={} agent={} chat_id={}",
            ws_conn_id,
            coords.user_id,
            coords.agent_id,
            coords.chat_row_id,
        )
        return True

    logger.info(
        "companion_ws_monolog_inner_tick tool_bg_only ws_conn_id={} user={} "
        "agent={} chat_id={}",
        ws_conn_id,
        coords.user_id,
        coords.agent_id,
        coords.chat_row_id,
    )
    return True


async def try_fire_dreaming_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """When companion scope may be due for sleeping-state dreaming, run one batch."""
    coords = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.DREAMING_HARNESS,
    )
    if coords is None:
        return False

    mem_store = companion_chat_service.companion_memory_store_if_ready(
        user_id=coords.user_id,
        agent_id=coords.agent_id,
        chat_id=coords.chat_row_id,
        resolved_chat_model=coords.model_override,
    )
    if mem_store is None:
        return False

    idle_seconds = (
        global_config_loaded_from_config_yaml.agent.companion_harness.dreaming_idle_seconds
    )

    scope_session = (
        await companion_chat_service.resolve_companion_session_for_api_turn(
            user_id=coords.user_id,
            agent_id=coords.agent_id,
            chat_id=coords.chat_row_id,
            resolved_chat_model=coords.model_override,
            session_id=None,
        )
    )
    async with inner_tick_turn_scope(session=scope_session):
        outcome = await asyncio.to_thread(
            companion_chat_service.run_dreaming_batch_for_api,
            user_id=coords.user_id,
            agent_id=coords.agent_id,
            chat_id=coords.chat_row_id,
            resolved_chat_model=coords.model_override,
            dreaming_idle_seconds=idle_seconds,
        )
        if outcome == DreamingBatchOutcome.CHECKPOINT_SAVED:
            logger.info(
                "companion_ws_dreaming checkpoint_saved ws_conn_id={} user={} "
                "agent={} chat={}",
                fire_input.ws_conn_id,
                coords.user_id,
                coords.agent_id,
                coords.chat_row_id,
            )
        return outcome == DreamingBatchOutcome.CHECKPOINT_SAVED
