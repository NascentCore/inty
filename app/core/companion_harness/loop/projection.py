"""Project loop deliverables to channel-agnostic ``Downlink``."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
    InTurnInterimOutput,
)
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
    bootstrap_interim_downlink,
    tool_background_downlink,
)

from .output_queue import LoopDeliverable, LoopDeliverableKind


@dataclass(frozen=True)
class LoopProjectionContext:
    """Track-aware loop→downlink projection (bootstrap defers loop terminal)."""

    defer_terminal_user_reply: bool


def project_deliverable(deliverable: LoopDeliverable) -> Downlink:
    """Map one ``LoopDeliverable`` to a ``Downlink`` for ``LoopChannelAdapter``."""
    match deliverable.kind:
        case LoopDeliverableKind.INTERIM_REPLY | LoopDeliverableKind.BOOTSTRAP_INTERIM:
            interim = deliverable.bootstrap_interim
            assert interim is not None
            return bootstrap_interim_downlink(interim=interim)
        case LoopDeliverableKind.TOOL_BACKGROUND:
            assert deliverable.tool_output is not None
            return tool_background_downlink(tool_output=deliverable.tool_output)
        case LoopDeliverableKind.FOREGROUND_TEXT | LoopDeliverableKind.USER_REPLY:
            return Downlink(
                kind=DownlinkKind.USER_REPLY,
                assistant_text=deliverable.assistant_text,
                turn=_minimal_turn_result(
                    assistant_text=deliverable.assistant_text,
                    significance_perception=deliverable.significance_meta,
                    turn_recall=deliverable.turn_recall,
                ),
                tool_output=None,
                bootstrap_interim=None,
                scheduled_task_id=None,
                transcript_user_text=None,
            )
        case _:
            raise AssertionError(f"unknown deliverable kind: {deliverable.kind}")


def interim_output_from_dataclass(interim: InTurnInterimOutput) -> BootstrapInterimOutput:
    """Wire ``InTurnInterimOutput`` → Pydantic for ``Downlink`` factories."""
    return BootstrapInterimOutput(
        text=interim.text,
        user_msg_uuid=interim.user_msg_uuid,
        trace_id=interim.trace_id,
        langsmith_trace_id=interim.langsmith_trace_id,
        langsmith_run_id=interim.langsmith_run_id,
        round_index=interim.round_index,
        had_tool_calls=interim.had_tool_calls,
        assistant_msg_uuid=interim.assistant_msg_uuid,
    )


def _minimal_turn_result(
    *,
    assistant_text: str,
    significance_perception: dict[str, object] | None,
    turn_recall: str | None,
) -> CompanionTurnResult:
    """Minimal turn shell for per-call USER_REPLY / foreground downlinks."""
    return CompanionTurnResult(
        assistant_text=assistant_text,
        significance_perception=significance_perception,
        turn_recall=turn_recall,
    )
