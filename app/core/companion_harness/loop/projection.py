"""Project loop deliverables to channel-agnostic ``Downlink``.

TODO(!3460): Delete with loop/output_queue.py after direct AgenticLoop
methods write user-visible content to agentic_companion OutputQueue.
"""

from __future__ import annotations

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
    bootstrap_interim_downlink,
    tool_background_downlink,
)

from .output_queue import LoopDeliverable, LoopDeliverableKind


def project_deliverable(deliverable: LoopDeliverable) -> Downlink:
    """Map one ``LoopDeliverable`` to a ``Downlink`` for ``LoopChannelAdapter``."""
    match deliverable.kind:
        case LoopDeliverableKind.BOOTSTRAP_INTERIM:
            assert deliverable.bootstrap_interim is not None
            return bootstrap_interim_downlink(
                interim=deliverable.bootstrap_interim
            )
        case LoopDeliverableKind.TOOL_BACKGROUND:
            assert deliverable.tool_output is not None
            return tool_background_downlink(tool_output=deliverable.tool_output)
        case (
            LoopDeliverableKind.FOREGROUND_TEXT | LoopDeliverableKind.USER_REPLY
        ):
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
            raise AssertionError(
                f"unknown deliverable kind: {deliverable.kind}"
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
