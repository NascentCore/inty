from __future__ import annotations

from app.core.companion_harness.memory import (
    memory_store_path_constants as path_constants,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    COMPANION_LLM_TOOLS_BY_NAME,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
    CompanionToolName,
    _SELECTABLE_EXPERIENCE_SESSION_INTENTS,
)
from app.core.companion_harness.memory.memory_store_path_constants import (
    COMPANIONSHIP_MD_REL,
    IDENTITY_MD_REL,
    LIFE_CURRENTS_MD_REL,
    MEMORY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    USER_MD_REL,
)

_CANONICAL_MD_REL_PATHS = frozenset(
    value
    for name, value in vars(path_constants).items()
    if name.endswith("_MD_REL") and isinstance(value, str)
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


def test_memory_store_write_allowlists_use_canonical_md_rel_paths() -> None:
    for rel in (
        *MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
        *MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        *MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    ):
        assert rel in _CANONICAL_MD_REL_PATHS


def test_memory_store_write_allowlist_autonomy_is_life_currents_only() -> None:
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY == frozenset(
        {LIFE_CURRENTS_MD_REL}
    )


def test_memory_store_write_allowlist_user_chat_paths() -> None:
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST == frozenset(
        {
            COMPANIONSHIP_MD_REL,
            IDENTITY_MD_REL,
            LIFE_CURRENTS_MD_REL,
            MEMORY_MD_REL,
            SOUL_MD_REL,
            STYLE_MD_REL,
            USER_MD_REL,
        }
    )


def test_memory_store_write_allowlist_bootstrap_paths() -> None:
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP == frozenset(
        {
            COMPANIONSHIP_MD_REL,
            IDENTITY_MD_REL,
            STYLE_MD_REL,
            USER_MD_REL,
        }
    )


def test_jsonl_tool_descriptions_use_scope_accessor_paths() -> None:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    ai_private = COMPANION_LLM_TOOLS_BY_NAME[
        CompanionToolName.AI_PRIVATE_APPEND.value
    ]
    living_sphere = COMPANION_LLM_TOOLS_BY_NAME[
        CompanionToolName.LIVING_SPHERE_RECORD_UPDATE.value
    ]
    techno_core = COMPANION_LLM_TOOLS_BY_NAME[
        CompanionToolName.TECHNO_CORE_RECORD_EVENT.value
    ]
    assert paths.ai_private_jsonl in ai_private.description
    assert paths.living_sphere_updates_jsonl in living_sphere.description
    assert paths.techno_core_events_jsonl in techno_core.description
