from __future__ import annotations

from app.core.companion_harness.memory import (
    memory_store_path_constants as path_constants,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
    _SELECTABLE_EXPERIENCE_SESSION_INTENTS,
)
from app.core.companion_harness.memory.memory_store_path_constants import (
    LIFE_CURRENTS_MD_REL,
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
