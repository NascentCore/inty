from __future__ import annotations

from app.core.companion_harness.tools.companion_tool_definitions import (
    _SELECTABLE_EXPERIENCE_PROFILE_IDS,
)


def test_selectable_experience_profile_ids_matches_non_bootstrap_enum_members() -> None:
    assert _SELECTABLE_EXPERIENCE_PROFILE_IDS == (
        "emotional_companion",
        "interactive_fiction",
        "intimate",
        "public",
        "remote_lover",
        "roleplay",
        "unspecific",
    )
