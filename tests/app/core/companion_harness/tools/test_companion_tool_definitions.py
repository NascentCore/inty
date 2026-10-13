from __future__ import annotations

from app.core.companion_harness.memory import (
    memory_store_path_constants as path_constants,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
    _SELECTABLE_EXPERIENCE_SESSION_INTENTS,
)

_CANONICAL_MD_REL_PATHS = frozenset(
    value
    for name, value in vars(path_constants).items()
    if name.endswith("_MD_REL") and isinstance(value, str)
)

_SCOPE = DEFAULT_MEMORY_STORE_SCOPE_PATHS


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
        {_SCOPE.life_currents_md}
    )


def test_memory_store_write_allowlist_user_chat_paths() -> None:
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST == frozenset(
        {
            _SCOPE.companionship_md,
            _SCOPE.identity,
            _SCOPE.life_currents_md,
            _SCOPE.memory_md,
            _SCOPE.soul,
            _SCOPE.style_md,
            _SCOPE.user_md,
        }
    )


def test_memory_store_write_allowlist_bootstrap_paths() -> None:
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP == frozenset(
        {
            _SCOPE.companionship_md,
            _SCOPE.identity,
            _SCOPE.style_md,
            _SCOPE.user_md,
        }
    )

