"""Turn initiation kind for prompt system-prefix assembly gates."""

from __future__ import annotations

from enum import StrEnum


class PromptComposeTrigger(StrEnum):
    """What initiated the companion turn whose system prefix is being composed."""

    USER_MESSAGE = "user_message"
    SYSTEM_INITIATED = "system_initiated"
