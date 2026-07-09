"""Turn initiation kind for prompt system-prefix assembly gates."""

from __future__ import annotations

from enum import StrEnum

from app.core.companion_harness.companion.models import CompanionTurnTrack


class PromptComposeTrigger(StrEnum):
    """What initiated the companion turn whose system prefix is being composed."""

    USER_MESSAGE = "user_message"
    SYSTEM_INITIATED = "system_initiated"


def compose_trigger_for_track(track: CompanionTurnTrack) -> PromptComposeTrigger:
    """Derive compose trigger from production turn track."""
    match track:
        case (
            CompanionTurnTrack.USER_CHAT
            | CompanionTurnTrack.USER_CHAT_BOOTSTRAP
        ):
            return PromptComposeTrigger.USER_MESSAGE
        case _:
            return PromptComposeTrigger.SYSTEM_INITIATED
