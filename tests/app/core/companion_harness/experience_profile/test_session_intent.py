"""Tests for experience session intent → context_mode mapping."""

from __future__ import annotations

import pytest

from app.core.companion_harness.experience_profile.context_mode import (
    ExperienceContextMode,
)
from app.core.companion_harness.experience_profile.experience_directives import (
    ExperienceSessionIntent,
    context_mode_for_session_intent,
)


@pytest.mark.parametrize(
    ("intent", "expected_context_mode"),
    [
        (ExperienceSessionIntent.CASUAL_CHAT, ExperienceContextMode.EMOTIONAL_COMPANION.value),
        (ExperienceSessionIntent.DEEP_CONVERSATION, ExperienceContextMode.INTIMATE.value),
        (ExperienceSessionIntent.ROLEPLAY, ExperienceContextMode.ROLEPLAY.value),
        (ExperienceSessionIntent.EMOTIONAL_SUPPORT, ExperienceContextMode.EMOTIONAL_COMPANION.value),
        (ExperienceSessionIntent.REMOTE_ROMANCE, ExperienceContextMode.REMOTE_LOVER.value),
        (
            ExperienceSessionIntent.INTERACTIVE_FICTION,
            ExperienceContextMode.INTERACTIVE_FICTION.value,
        ),
    ],
)
def test_context_mode_for_session_intent_maps_all_members(
    intent: ExperienceSessionIntent,
    expected_context_mode: str,
) -> None:
    assert context_mode_for_session_intent(intent) == expected_context_mode
