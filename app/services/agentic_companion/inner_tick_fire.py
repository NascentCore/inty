"""Inner-tick glue: presence coordinator guards, harness runtime, chat_history persist.

Orchestrates ``companion_harness.runtime.inner_tick_fire`` (kernel due + turn),
``inner_tick_scope`` (ORM), and ``inner_tick_deliver`` (chat_history only).
Channel delivery is pump-owned via OutputQueue.

Locking: each ``try_fire_*`` acquires **scope** ``CompanionSession.turn_lock`` (#3272).
User chat on the same scope also holds that lock — inner ticks (including dreaming) and
user messages serialize per ``(user_id, agent_id, chat_id)``. Prototype: single presence
per paired user (``companion_harness`` AGENTS.md).

TODO(!3516): Simplify scope serialization and foreground-pending skip rules during
the AgenticLoop + InputQueue/OutputQueue + Channel overhaul.

Prototype: inner-tick fire paths do not call ``subscription_service`` (no
``check_chat_limit`` / ``record_usage``). User chat billing stays in ``chat_ws.py``.
"""

from __future__ import annotations

import uuid

from loguru import logger

from app.core.companion_harness.companion.inner_tick_kind import InnerTickKind
from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.runtime.inner_tick_fire import (
    InnerTickKernelInput,
    InnerTickThrottleSnapshot,
    due_scheduled_task,
    kernel_fire_proactive,
    kernel_fire_scheduled,
    proactive_chat_remain_seconds,
)
from app.schemas.chat_websocket import (
    build_inner_tick_wire_meta,
)
from app.services.chat_service import generate_session_id
from app.services.agentic_companion.inner_tick_deliver import (
    InnerTickVisiblePersistInput,
    persist_visible_inner_tick_turn,
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

_EMPTY_THROTTLE_SNAPSHOT = InnerTickThrottleSnapshot(
    last_monolog_monotonic=None,
    last_monolog_line_count=None,
    last_autonomy_monotonic=None,
    last_autonomy_line_count=None,
)


async def _kernel_context(
    coords: InnerTickScopeCoords,
    fire_input: InnerTickFireInput,
    *,
    preset_uid: str,
) -> tuple[InnerTickKernelInput, CompanionSession] | None:
    ws_implicit = implicit_signal_bundle_from_tc_box(fire_input.tc_box)
    return await build_inner_tick_kernel_context(
        user_id=coords.user_id,
        agent_id=coords.agent_id,
        chat_row_id=coords.chat_row_id,
        model_override=coords.model_override,
        throttle=_EMPTY_THROTTLE_SNAPSHOT,
        runtime_context=TurnRuntimeContext(
            channel=fire_input.runtime_channel,
            implicit_signal_bundle=ws_implicit,
        ),
        preset_uid=preset_uid,
    )


async def try_fire_scheduled_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    # TODO(#3473): gate proactive + scheduled fire on token budget before turn_lock.
    """When ``schedule_queue`` has a due pending task, run one inner-tick reminder turn."""
    coords = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    if coords is None:
        return False

    preset_uid = str(uuid.uuid4())
    ctx_pair = await _kernel_context(coords, fire_input, preset_uid=preset_uid)
    if ctx_pair is None:
        return False
    kernel_input, scope_session = ctx_pair

    ws_conn_id = fire_input.ws_conn_id
    session_id = generate_session_id(str(coords.chat_row_id))

    async with inner_tick_turn_scope(session=scope_session):
        due_task = due_scheduled_task(kernel_input.mem_store)
        if due_task is None:
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

        delivered = await persist_visible_inner_tick_turn(
            InnerTickVisiblePersistInput(
                session_id=session_id,
                chat_row_agent_id=coords.chat_row_agent_id,
                preset_uid=preset_uid,
                transcript_user_text=kernel_result.transcript_user_text,
                companion_turn=companion_turn,
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
    ctx_pair = await _kernel_context(coords, fire_input, preset_uid=preset_uid)
    if ctx_pair is None:
        return False
    kernel_input, scope_session = ctx_pair

    if proactive_chat_remain_seconds(kernel_input.mem_store) > 0:
        return False

    ws_conn_id = fire_input.ws_conn_id
    session_id = generate_session_id(str(coords.chat_row_id))

    async with inner_tick_turn_scope(session=scope_session):
        kernel_result = await kernel_fire_proactive(kernel_input)
        companion_turn = kernel_result.turn

        delivered = await persist_visible_inner_tick_turn(
            InnerTickVisiblePersistInput(
                session_id=session_id,
                chat_row_agent_id=coords.chat_row_agent_id,
                preset_uid=preset_uid,
                transcript_user_text=kernel_result.transcript_user_text,
                companion_turn=companion_turn,
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
