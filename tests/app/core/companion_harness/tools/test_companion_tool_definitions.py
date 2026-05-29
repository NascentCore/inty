from __future__ import annotations

from app.core.companion_harness.tools.companion_tool_definitions import (
    COMPANION_LLM_TOOLS_BY_NAME,
    INNER_TICK_TOOL_NAMES,
    TOOL_NAMES_NON_BOOTSTRAP_TAIL,
    CompanionToolName,
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


def test_record_user_feedback_is_maintenance_track_only() -> None:
    # Feedback recording is an inner-tick maintenance reflection, kept off the user-chat reply path.
    assert CompanionToolName.RECORD_USER_FEEDBACK in INNER_TICK_TOOL_NAMES
    assert CompanionToolName.RECORD_USER_FEEDBACK not in TOOL_NAMES_NON_BOOTSTRAP_TAIL
    assert CompanionToolName.RECORD_USER_FEEDBACK in COMPANION_LLM_TOOLS_BY_NAME
