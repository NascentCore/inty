from __future__ import annotations

from app.core.companion_harness.tools.companion_tool_definitions import (
    _SELECTABLE_EXPERIENCE_SESSION_INTENTS,
)


def test_selectable_experience_session_intents_matches_enum_members() -> None:
    assert _SELECTABLE_EXPERIENCE_SESSION_INTENTS == (
        "casual_chat",
        "deep_conversation",
        "emotional_support",
        "interactive_fiction",
        "remote_romance",
        "roleplay",
    )
