from __future__ import annotations

from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    AI_PRIVATE_APPEND_TOOL,
    LIVING_SPHERE_RECORD_UPDATE_TOOL,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
    TECHNO_CORE_RECORD_EVENT_TOOL,
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


def test_memory_store_write_allowlists_match_scope_accessor_rel_paths() -> None:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST == frozenset(
        {
            paths.companionship_md,
            paths.identity,
            paths.life_currents_md,
            paths.memory_md,
            paths.soul,
            paths.style_md,
            paths.user_md,
        }
    )
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP == frozenset(
        {
            paths.companionship_md,
            paths.identity,
            paths.style_md,
            paths.user_md,
        }
    )
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY == frozenset(
        {paths.life_currents_md}
    )


def test_tool_description_jsonl_paths_match_scope_accessors() -> None:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    assert paths.ai_private_jsonl in AI_PRIVATE_APPEND_TOOL.description
    assert paths.living_sphere_updates_jsonl in LIVING_SPHERE_RECORD_UPDATE_TOOL.description
    assert paths.techno_core_events_jsonl in TECHNO_CORE_RECORD_EVENT_TOOL.description
