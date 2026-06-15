"""When ``OutputQueue`` deliverables reach ``Channel.deliver``."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.companion_harness.companion.models import CompanionTurnTrack

from .loop_deliverable import LoopDeliverable, LoopDeliverableKind


class TerminalReplyDelivery(StrEnum):
    """Bootstrap defers terminal ``USER_REPLY`` until queue close."""

    IMMEDIATE = "immediate"
    ON_QUEUE_CLOSE = "on_queue_close"


@dataclass(frozen=True)
class DeliveryPolicy:
    """Queue-bound outbound timing for terminal user-visible replies."""

    terminal_reply_delivery: TerminalReplyDelivery

    def holds_terminal_reply(self, deliverable: LoopDeliverable) -> bool:
        """True when delivery task must buffer ``USER_REPLY`` until flush."""
        return (
            self.terminal_reply_delivery
            is TerminalReplyDelivery.ON_QUEUE_CLOSE
            and deliverable.kind is LoopDeliverableKind.USER_REPLY
        )


def delivery_policy_for_turn_track(track: CompanionTurnTrack) -> DeliveryPolicy:
    """Factory: bootstrap uses ``ON_QUEUE_CLOSE`` terminal delivery."""
    terminal = (
        TerminalReplyDelivery.ON_QUEUE_CLOSE
        if track is CompanionTurnTrack.USER_CHAT_BOOTSTRAP
        else TerminalReplyDelivery.IMMEDIATE
    )
    return DeliveryPolicy(terminal_reply_delivery=terminal)
