"""Inner-tick AwakeTurn orchestration at Companion Harness runtime layer.

Due checks and kernel ``run_inner_tick_*`` execution only. Callers must hold
scope ``CompanionSession.turn_lock``. Chat history, WebSocket payloads, and ORM
scope resolution belong in ``app.services.agentic_companion`` glue.

TODO(world-engine-firefly-clock): Activate firefly per-agent clock in production — #3707
(inner-tick summon path); independent cadence from companion (epic #3700).

TODO(world-engine-tracer-bullet): E2E tracer bullet — idle user → summon → firefly — #3711
tick → mailbox → dismiss + MEMORY echo → user hears about it (epic #3700).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.inner_tick_kind import (
    InnerTickKind,
    inner_tick_spec,
)
from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    monolog_transcript_line_count,
    next_inner_tick_wait_seconds,
)
from app.core.companion_harness.companion.manager import (
    CompanionManager,
    CompanionSession,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnResult,
    InnerTickThrottleKind,
)
from app.core.companion_harness.companion.proactive_chat import (
    PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER,
    ProactiveChatConfig,
    next_proactive_chat_wait_seconds,
)
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.schedule_queue import (
    ScheduleTask,
    mark_task_fired,
    mark_task_retry,
    next_due_task_for_execution,
    scheduled_task_synthetic_user_text,
)
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputQueue,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.config import global_config_loaded_from_config_yaml


@dataclass(frozen=True)
class InnerTickThrottleSnapshot:
    """Presence-agnostic throttle state for monolog and autonomy inner ticks."""

    last_monolog_monotonic: Any
    last_monolog_line_count: int | None
    last_autonomy_monotonic: Any
    last_autonomy_line_count: int | None

    def throttle_remain_inputs(
        self,
        kind: InnerTickKind,
    ) -> tuple[Any, int | None]:
        """Return ``(last_fire_monotonic, last_transcript_line_count)`` for ``kind``."""
        match kind:
            case InnerTickKind.MONOLOG:
                return (
                    self.last_monolog_monotonic,
                    self.last_monolog_line_count,
                )
            case InnerTickKind.AUTONOMY:
                return (
                    self.last_autonomy_monotonic,
                    self.last_autonomy_line_count,
                )
            case InnerTickKind.PROACTIVE_CHAT | InnerTickKind.SCHEDULED:
                raise ValueError(
                    f"throttle_remain_inputs unsupported for {kind.value}"
                )


@dataclass(frozen=True)
class InnerTickKernelInput:
    """Arguments for one in-lock inner-tick kernel fire attempt.

    Carries no ``UserMessageBatch``: the manager turn entry synthesizes the
    batch from ``preset_user_msg_uuid`` with the concrete turn-track label.
    """

    manager: CompanionManager
    session: CompanionSession
    mem_store: MemoryStore
    throttle: InnerTickThrottleSnapshot
    runtime_context: TurnRuntimeContext
    preset_user_msg_uuid: str
    agentic_output_queue: OutputQueue


@dataclass(frozen=True)
class InnerTickKernelResult:
    """Kernel turn outcome for channel glue to persist and deliver."""

    turn: CompanionTurnResult
    track_path: str
    transcript_user_text: str
    scheduled_task_id: str | None
    throttle_line_count: int | None
    throttle_kind: InnerTickThrottleKind | None


def _monolog_schedule_overrides() -> InnerTickScheduleOverrides:
    harness = global_config_loaded_from_config_yaml.agent.companion_harness
    return InnerTickScheduleOverrides(
        enabled=True,
        min_gap_seconds=float(harness.inner_tick.monolog.min_gap_seconds),
        poll_seconds=float(harness.inner_tick.proactive_chat.poll_seconds),
    )


def proactive_chat_remain_seconds(mem_store: MemoryStore) -> float:
    """Seconds until proactive chat is due; ``0`` means due now."""
    harness = global_config_loaded_from_config_yaml.agent.companion_harness
    proactive = harness.inner_tick.proactive_chat
    return next_proactive_chat_wait_seconds(
        mem_store,
        ProactiveChatConfig(
            base_idle_sec=float(proactive.base_idle_seconds),
            stop_after_silence_minutes=float(
                proactive.stop_after_silence_minutes
            ),
        ),
    )


def inner_tick_remain_seconds(
    kind: InnerTickKind,
    mem_store: MemoryStore,
    throttle: InnerTickThrottleSnapshot,
) -> float:
    """Seconds until ``kind`` inner-tick is due; ``0`` means due now."""
    spec = inner_tick_spec(kind)
    assert spec.throttle_kind is not None
    last_fire_monotonic, last_line_count = throttle.throttle_remain_inputs(kind)
    return next_inner_tick_wait_seconds(
        mem_store,
        last_inner_fire_monotonic=last_fire_monotonic,
        last_monolog_transcript_line_count=last_line_count,
        overrides=_monolog_schedule_overrides(),
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
        companion_turn = (
            await kernel_input.manager.run_inner_tick_scheduled_turn(
                kernel_input.session,
                synthetic_user_text,
                preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
                runtime_context=kernel_input.runtime_context,
                agentic_output_queue=kernel_input.agentic_output_queue,
            )
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
    companion_turn = (
        await kernel_input.manager.run_inner_tick_proactive_chat_turn(
            kernel_input.session,
            preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
            runtime_context=kernel_input.runtime_context,
            agentic_output_queue=kernel_input.agentic_output_queue,
        )
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


# TODO(#3468): AUTONOMY durable artifacts (LIFE_CURRENTS, TC/LS events, generated_images)
# must shape the next user-visible turn — fixture trace 019ed438 (see issue attachment).
async def kernel_fire_throttled(
    kind: InnerTickKind,
    kernel_input: InnerTickKernelInput,
) -> InnerTickKernelResult:
    """Run one throttled inner-tick turn for ``kind``; caller holds ``turn_lock``."""
    spec = inner_tick_spec(kind)
    throttle_line_count: int | None = None
    if spec.throttle_kind is not None:
        throttle_line_count = monolog_transcript_line_count(
            kernel_input.mem_store
        )

    match kind:
        case InnerTickKind.MONOLOG:
            companion_turn = (
                await kernel_input.manager.run_inner_tick_monolog_turn(
                    kernel_input.session,
                    preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
                    runtime_context=kernel_input.runtime_context,
                    agentic_output_queue=kernel_input.agentic_output_queue,
                )
            )
            reply_stripped = str(companion_turn.assistant_text or "").strip()
            if (
                not reply_stripped
                and not companion_turn.tool_background_started
            ):
                logger.info("inner_tick_monolog kernel monolog_empty")
        case InnerTickKind.AUTONOMY:
            companion_turn = (
                await kernel_input.manager.run_inner_tick_autonomy_turn(
                    kernel_input.session,
                    preset_user_msg_uuid=kernel_input.preset_user_msg_uuid,
                    runtime_context=kernel_input.runtime_context,
                    agentic_output_queue=kernel_input.agentic_output_queue,
                )
            )
        case InnerTickKind.PROACTIVE_CHAT | InnerTickKind.SCHEDULED:
            raise ValueError(
                f"kernel_fire_throttled unsupported for {kind.value}; "
                "use kernel_fire_proactive or kernel_fire_scheduled"
            )

    return InnerTickKernelResult(
        turn=companion_turn,
        track_path=spec.turn_track.value,
        transcript_user_text=spec.chat_history_marker,
        scheduled_task_id=None,
        throttle_line_count=throttle_line_count,
        throttle_kind=spec.throttle_kind,
    )
