"""Companion foreground user-turn input (text-only phase; multimodal #3293 later)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanionUserTurnInput:
    """Normalized user text for one companion user-chat turn."""

    text: str

    def to_transcript_text(self) -> str:
        """Text persisted on the user transcript row."""
        assert self.text.strip()
        return self.text
