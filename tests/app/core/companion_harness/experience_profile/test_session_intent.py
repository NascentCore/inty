"""Tests for experience session intent → context_mode mapping."""

from __future__ import annotations

from app.core.companion_harness.experience_profile.context_mode import (
    ExperienceContextMode,
)
from app.core.companion_harness.experience_profile.experience_directives import (
    ExperienceSessionIntent,
    context_mode_for_session_intent,
)


def test_context_mode_for_session_intent_deep_conversation() -> None:
    assert (
        context_mode_for_session_intent(ExperienceSessionIntent.DEEP_CONVERSATION)
        == ExperienceContextMode.INTIMATE.value
    )


def test_context_mode_for_session_intent_roleplay() -> None:
    assert (
        context_mode_for_session_intent(ExperienceSessionIntent.ROLEPLAY)
        == ExperienceContextMode.ROLEPLAY.value
    )
