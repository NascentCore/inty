"""Inner-tick AwakeTurn orchestration at Companion Harness runtime layer.

Due checks and kernel ``run_inner_tick_*`` execution only. Callers must hold
scope ``CompanionSession.turn_lock``. Chat history, WebSocket payloads, and ORM
scope resolution belong in ``app.services.agentic_companion`` glue.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    maintenance_transcript_line_count,
    next_inner_tick_wait_seconds,
)
from app.core.companion_harness.companion.manager import (
    CompanionManager,
    CompanionSession,
)
from app.core.companion_harness.companion.models import (
    MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER,
    CompanionTurnResult,
)
from app.core.companion_harness.companion.proactive_chat import (
    PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER,
    ProactiveChatConfig,
    next_proactive_chat_wait_seconds,
)
from app.core.companion_harness.companion.runtime_channel import TurnRuntimeContext
from app.core.companion_harness.companion.schedule_queue import (
    ScheduleTask,
    mark_task_fired,
    mark_task_retry,
    next_due_task_for_execution,
    scheduled_task_synthetic_user_text,
)
from app.core.companion_harness.companion.turn_routes import BackgroundToolEventSink
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.config import global_config_loaded_from_config_yaml


class InnerTickThrottleKind(StrEnum):
    """Which inner-tick throttle counter glue should update after a kernel fire."""

    MAINTENANCE = "maintenance"
    AUTONOMY = "autonomy"


@dataclass(frozen=True)
class InnerTickThrottleSnapshot:
    """Presence-agnostic throttle state for maintenance and autonomy inner ticks."""

    last_maintenance_monotonic: Any
    last_maintenance_line_count: int | None
    last_autonomy_monotonic: Any
    last_autonomy_line_count: int | None


@dataclass(frozen=True)
class InnerTickKernelInput:
    """Arguments for one in-lock inner-tick kernel fire attempt."""

    manager: CompanionManager
    session: CompanionSession
    mem_store: MemoryStore
    throttle: InnerTickThrottleSnapshot
    runtime_context: TurnRuntimeContext
    preset_user_msg_uuid: str
    background_output_sink: BackgroundToolEventSink | None


@dataclass(frozen=True)
class InnerTickKernelResult:
    """Kernel turn outcome for channel glue to persist and deliver."""

    turn: CompanionTurnResult
    track_path: str
    transcript_user_text: str
    scheduled_task_id: str | None
    throttle_line_count: int | None
    throttle_kind: InnerTickThrottleKind | None


def _maintenance_schedule_overrides() -> InnerTickScheduleOverrides:
    feats = global_config_loaded_from_config_yaml.app.features
    return InnerTickScheduleOverrides(
        enabled=True,
        min_gap_seconds=float(
            feats.companion_ws_maintenance_inner_tick_min_gap_seconds
        ),
        poll_seconds=float(feats.companion_ws_proactive_chat_poll_seconds),
    )


def proactive_chat_remain_seconds(mem_store: MemoryStore) -> float:
    """Seconds until proactive chat is due; ``0`` means due now."""
    feats = global_config_loaded_from_config_yaml.app.features
    return next_proactive_chat_wait_seconds(
        mem_store,
        ProactiveChatConfig(
            base_idle_sec=float(
                feats.companion_ws_proactive_chat_base_idle_seconds
            ),
            stop_after_silence_minutes=float(
                feats.companion_ws_proactive_chat_stop_after_silence_minutes
            ),
        ),
    )


def maintenance_inner_tick_remain_seconds(
    mem_store: MemoryStore,
    throttle: InnerTickThrottleSnapshot,
) -> float:
    """Seconds until maintenance inner-tick is due; ``0`` means due now."""
    return next_inner_tick_wait_seconds(
        mem_store,
        last_inner_fire_monotonic=throttle.last_maintenance_monotonic,
        last_maintenance_transcript_line_count=throttle.last_maintenance_line_count,
        overrides=_maintenance_schedule_overrides(),
    )


def autonomy_inner_tick_remain_seconds(
    mem_store: MemoryStore,
    throttle: InnerTickThrottleSnapshot,
) -> float:
    """Seconds until autonomy inner-tick is due; ``0`` means due now."""
    return next_inner_tick_wait_seconds(
        mem_store,
        last_inner_fire_monotonic=throttle.last_autonomy_monotonic,
        last_maintenance_transcript_line_count=throttle.last_autonomy_line_count,
        overrides=_maintenance_schedule_overrides(),
    )


def due_scheduled_task(mem_store: MemoryStore) -> ScheduleTask | None:
    """Return the next due schedule-queue task, if any."""
    return next_due_task_for_execution(mem_store)


async def kernel_fire_scheduled(
    kernel_input: InnerTickKernelInput,
    due_task: ScheduleTask,
) -> InnerTickKernelResult | None:
    """Run one scheduled reminder inner-tick turn; caller holds ``turn_lock``."""
    synthetic_user_text = scheduled_task_synthetic_user_text(
        task_text=due_task.task_text,
        exec_time_utc=due_task.exec_time_utc,
    )
    try:
        companion_turn = await kernel_input.manager.run_inner_tick_scheduled_turn(
            kernel_input.session,
            synthetic_user_text,
            background_output_sink=None,
            preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
            runtime_context=kernel_input.runtime_context,
        )
    except Exception as exc:
        if not getattr(exc, "companion_tool_background_started", False):
            mark_task_retry(kernel_input.mem_store, due_task.id, str(exc))
        raise

    reply_stripped = str(companion_turn.assistant_text or "").strip()
    if not reply_stripped:
        mark_task_retry(
            kernel_input.mem_store, due_task.id, "empty assistant reply"
        )
        return None

    mark_task_fired(kernel_input.mem_store, due_task.id)
    return InnerTickKernelResult(
        turn=companion_turn,
        track_path="inner_tick_scheduled",
        transcript_user_text=synthetic_user_text,
        scheduled_task_id=due_task.id,
        throttle_line_count=None,
        throttle_kind=None,
    )


async def kernel_fire_proactive(
    kernel_input: InnerTickKernelInput,
) -> InnerTickKernelResult:
    """Run one proactive chat inner-tick turn; caller holds ``turn_lock``."""
    companion_turn = await kernel_input.manager.run_inner_tick_proactive_chat_turn(
        kernel_input.session,
        background_output_sink=None,
        preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
        runtime_context=kernel_input.runtime_context,
    )
    hb_user_text = (
        companion_turn.transcript_user_content
        or PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER
    )
    return InnerTickKernelResult(
        turn=companion_turn,
        track_path="inner_tick_proactive_chat",
        transcript_user_text=hb_user_text,
        scheduled_task_id=None,
        throttle_line_count=None,
        throttle_kind=None,
    )


async def kernel_fire_autonomy(
    kernel_input: InnerTickKernelInput,
) -> InnerTickKernelResult:
    """Run one autonomy inner-tick turn; caller holds ``turn_lock``."""
    line_count = maintenance_transcript_line_count(kernel_input.mem_store)
    companion_turn = await kernel_input.manager.run_inner_tick_autonomy_turn(
        kernel_input.session,
        background_output_sink=kernel_input.background_output_sink,
        preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
        runtime_context=kernel_input.runtime_context,
    )
    return InnerTickKernelResult(
        turn=companion_turn,
        track_path="inner_tick_autonomy",
        transcript_user_text="",
        scheduled_task_id=None,
        throttle_line_count=line_count,
        throttle_kind=InnerTickThrottleKind.AUTONOMY,
    )


async def kernel_fire_maintenance(
    kernel_input: InnerTickKernelInput,
) -> InnerTickKernelResult | None:
    """Run one maintenance inner-tick turn; caller holds ``turn_lock``."""
    line_count = maintenance_transcript_line_count(kernel_input.mem_store)
    companion_turn = await kernel_input.manager.run_inner_tick_maintenance_turn(
        kernel_input.session,
        background_output_sink=kernel_input.background_output_sink,
        preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
        runtime_context=kernel_input.runtime_context,
    )
    reply_stripped = str(companion_turn.assistant_text or "").strip()
    if not reply_stripped and not companion_turn.tool_background_started:
        logger.info("inner_tick_maintenance kernel monolog_empty")

    return InnerTickKernelResult(
        turn=companion_turn,
        track_path="inner_tick_maintenance",
        transcript_user_text=MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER,
        scheduled_task_id=None,
        throttle_line_count=line_count,
        throttle_kind=InnerTickThrottleKind.MAINTENANCE,
    )
