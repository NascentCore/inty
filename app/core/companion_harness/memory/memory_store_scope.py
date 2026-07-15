"""MemoryStore logical paths: template seeds and initialization checks (no filesystem scope root)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from .memory_store_path_constants import (
    ABOUT_MD_REL,
    CHANNELS_MD_REL,
    COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL,
    COMPANION_DREAMING_STATE_JSON_REL,
    COMPANION_LIVING_SPHERE_CURATOR_JSON_REL,
    COMPANION_SCHEDULE_TASKS_JSON_REL,
    COMPANIONSHIP_MD_REL,
    CONTEXT_JSON_REL,
    IDENTITY_MD_REL,
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL,
    INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL,
    INTY_V2_SCHEDULE_TASKS_JSON_REL,
    LIVING_SPHERE_MD_REL,
    MEMORY_MD_REL,
    SIGNIFICANCE_PERCEPTION_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    TECHNO_CORE_MD_REL,
    TOOLS_MD_REL,
    TRANSCRIPT_INNER_TICK_JSONL_REL,
    TRANSCRIPT_JSONL_REL,
    USER_MD_REL,
)
from .memory_store import MemoryStore

_MEMORY_PKG_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _MEMORY_PKG_DIR / "templates"
_PROMPTS_DIR = _MEMORY_PKG_DIR.parent / "companion" / "prompts"
_PACKAGE_PROMPT_SEED_FILES: Final[frozenset[str]] = frozenset(
    {
        ABOUT_MD_REL,
        "AXIOM.md",
        "BOOTSTRAP.md",
        CHANNELS_MD_REL,
        "HARNESS.md",
        "INTY.md",
        "OUTPUT_FORMAT_IM_DM.md",
        "SAFETY.md",
        TOOLS_MD_REL,
        SIGNIFICANCE_PERCEPTION_MD_REL,
    }
)
# TODO(static-prompt-slice-memstore): Split static prompt-slice seeds (HARNESS, TOOLS, …) from — #3506
# mutable MemDoc seeds; persist static kinds in MemoryStore on init. #3506


def load_template_seed_text(filename: str) -> str:
    base = (
        _PROMPTS_DIR
        if filename in _PACKAGE_PROMPT_SEED_FILES
        else _TEMPLATES_DIR
    )
    path = base / filename
    if not path.is_file():
        raise FileNotFoundError(f"missing memory template seed file: {path}")
    body = path.read_text(encoding="utf-8").rstrip() + "\n"
    assert (
        body.strip()
    ), f"template seed file is empty after strip (catastrophic): {path}"
    return body


@lru_cache(maxsize=1)
def get_imate_axiom_system_text() -> str:
    """Product axiom from prompts/AXIOM.md; first system slice for iMate."""
    return load_template_seed_text("AXIOM.md").strip()


@lru_cache(maxsize=1)
def get_inty_facts_system_text() -> str:
    """Inty ontology and philosophy from prompts/INTY.md; fixed system slice after AXIOM."""
    return load_template_seed_text("INTY.md").strip()


@lru_cache(maxsize=1)
def get_safety_system_text() -> str:
    """Interaction safety from prompts/SAFETY.md; final doctrine system slice."""
    return load_template_seed_text("SAFETY.md").strip()


@dataclass(frozen=True)
class MemoryStoreScopePaths:
    """Standard document paths as scope-relative posix strings (MemoryStore keys)."""

    state_file_prefix: str = ".companion"

    @property
    def identity(self) -> str:
        return IDENTITY_MD_REL

    @property
    def soul(self) -> str:
        return SOUL_MD_REL

    @property
    def style_md(self) -> str:
        return STYLE_MD_REL

    @property
    def user_md(self) -> str:
        return USER_MD_REL

    @property
    def memory_md(self) -> str:
        return MEMORY_MD_REL

    @property
    def channels_md(self) -> str:
        return CHANNELS_MD_REL

    @property
    def companionship_md(self) -> str:
        return COMPANIONSHIP_MD_REL

    @property
    def techno_core_md(self) -> str:
        return TECHNO_CORE_MD_REL

    @property
    def living_sphere_md(self) -> str:
        return LIVING_SPHERE_MD_REL

    @property
    def tools_md(self) -> str:
        return TOOLS_MD_REL

    @property
    def significance_perception_md(self) -> str:
        return SIGNIFICANCE_PERCEPTION_MD_REL

    @property
    def transcript(self) -> str:
        return TRANSCRIPT_JSONL_REL

    @property
    def transcript_inner_tick(self) -> str:
        # TODO(rename-memory-doc): Rename to transcript_inner_tick_monolog.jsonl — #3817
        # (monolog-only inner tick; update ORM mapping + migrations together).
        return TRANSCRIPT_INNER_TICK_JSONL_REL

    @property
    def context_json(self) -> str:
        return CONTEXT_JSON_REL

    def memory_daily_gist(self, day: str) -> str:
        """Daily gist path (``memory/daily/<date>.md``); written only by dreaming consolidation."""
        return f"memory/daily/{day}.md"

    @property
    def living_sphere_curator_state_json(self) -> str:
        match self.state_file_prefix:
            case ".companion":
                return COMPANION_LIVING_SPHERE_CURATOR_JSON_REL
            case ".inty_v2":
                return INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL
            case _:
                return f"{self.state_file_prefix}_living_sphere_curator.json"

    @property
    def context_compaction_state_json(self) -> str:
        match self.state_file_prefix:
            case ".companion":
                return COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL
            case ".inty_v2":
                return INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL
            case _:
                return f"{self.state_file_prefix}_context_compaction_state.json"

    @property
    def schedule_queue_json(self) -> str:
        match self.state_file_prefix:
            case ".companion":
                return COMPANION_SCHEDULE_TASKS_JSON_REL
            case ".inty_v2":
                return INTY_V2_SCHEDULE_TASKS_JSON_REL
            case _:
                return f"{self.state_file_prefix}_schedule_tasks.json"

    @property
    def dreaming_state_json(self) -> str:
        match self.state_file_prefix:
            case ".companion":
                return COMPANION_DREAMING_STATE_JSON_REL
            case _:
                return f"{self.state_file_prefix}_dreaming_state.json"


DEFAULT_MEMORY_STORE_SCOPE_PATHS = MemoryStoreScopePaths()

_REQUIRED_FILES_ATTR = (
    "identity",
    "soul",
    "user_md",
    "memory_md",
    "transcript",
)


def is_scope_initialized_in_store(store: MemoryStore) -> bool:
    """True when the five-piece exists in MemoryStore (production: DB-backed)."""
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    for attr in _REQUIRED_FILES_ATTR:
        rel = getattr(paths, attr)
        body = store.read_document_if_exists(rel)
        if attr == "transcript":
            if body is None:
                return False
            continue
        if body is None or not body.strip():
            return False
    return True


_MINIMAL_TRANSCRIPT_SEED = ""

# Canonical rel paths for core companion templates seeded into MemoryStore on init.
_CORE_COMPANION_TEMPLATE_REL_PATHS: Final[tuple[str, ...]] = (
    IDENTITY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    USER_MD_REL,
    MEMORY_MD_REL,
    CHANNELS_MD_REL,
    COMPANIONSHIP_MD_REL,
)


# TODO(person-identity-schema): Seed runtime USER.md + IDENTITY.md from generic templates/IDENTITY.md + role wrappers. #3390
def ensure_template_seeded_core_documents_in_store(store: MemoryStore) -> None:
    """
    Persist package templates for IDENTITY / SOUL / STYLE / USER / MEMORY when the store has no usable
    body (None or whitespace). Uses MemoryStore.write_document (repository append + cache).
    Does not touch transcript.jsonl; ``ensure_minimal_documents_in_store`` creates an
    empty transcript when the five-piece is not yet satisfied.
    """
    for rel in _CORE_COMPANION_TEMPLATE_REL_PATHS:
        body = store.read_document_if_exists(rel)
        if body is None or not body.strip():
            store.write_document(rel, load_template_seed_text(rel))


def ensure_minimal_documents_in_store(store: MemoryStore) -> None:
    """Write seed content for required paths into MemoryStore only (no disk authority)."""
    ensure_template_seeded_core_documents_in_store(store)
    if is_scope_initialized_in_store(store):
        return
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    for attr in _REQUIRED_FILES_ATTR:
        rel = getattr(paths, attr)
        body = store.read_document_if_exists(rel)
        if body is not None and body.strip():
            continue
        if attr == "transcript":
            store.write_document(rel, _MINIMAL_TRANSCRIPT_SEED)
        else:
            store.write_document(rel, load_template_seed_text(rel))
