"""MemoryStore logical paths: template seeds and initialization checks (no filesystem scope root)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Final

from loguru import logger

from .file_store import read_text
from .memory_document_catalog import (
    MEMORY_DAILY_DIR_RELATIVE_PATH,
    MEMORY_DIR_RELATIVE_PATH,
    scope_relative_path,
)
from .memory_store import MemoryStore, normalize_memory_store_relative_path

_MEMORY_PKG_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _MEMORY_PKG_DIR / "templates"
_PROMPTS_DIR = _MEMORY_PKG_DIR.parent / "companion" / "prompts"
_PACKAGE_PROMPT_SEED_FILES: Final[frozenset[str]] = frozenset(
    {
        "AXIOM.md",
        "BOOTSTRAP.md",
        "CHANNELS.md",
        "INTY.md",
        "OUTPUT_FORMAT_WECHAT_WEIXIN.md",
        "SAFETY.md",
        "TOOLS.md",
        "SIGNIFICANCE_PERCEPTION.md",
    }
)


def load_template_seed_text(filename: str) -> str:
    base = (
        _PROMPTS_DIR
        if filename in _PACKAGE_PROMPT_SEED_FILES
        else _TEMPLATES_DIR
    )
    path = base / filename
    if not path.is_file():
        raise FileNotFoundError(f"missing memory template seed file: {path}")
    body = read_text(path).rstrip() + "\n"
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

    def _path(self, scope_attr: str, *, day: str | None = None) -> str:
        return scope_relative_path(
            scope_attr,
            state_prefix=self.state_file_prefix,
            day=day,
        )

    @property
    def identity(self) -> str:
        return self._path("identity")

    @property
    def soul(self) -> str:
        return self._path("soul")

    @property
    def style_md(self) -> str:
        return self._path("style_md")

    @property
    def user_md(self) -> str:
        return self._path("user_md")

    @property
    def memory_md(self) -> str:
        return self._path("memory_md")

    @property
    def channels_md(self) -> str:
        return self._path("channels_md")

    @property
    def techno_core_md(self) -> str:
        return self._path("techno_core_md")

    @property
    def living_sphere_md(self) -> str:
        return self._path("living_sphere_md")

    @property
    def tools_md(self) -> str:
        return self._path("tools_md")

    @property
    def significance_perception_md(self) -> str:
        return self._path("significance_perception_md")

    @property
    def transcript(self) -> str:
        return self._path("transcript")

    @property
    def transcript_inner_tick(self) -> str:
        # TODO(rename-memory-doc): Rename to transcript_inner_tick_maintenance.jsonl
        # (maintenance-only inner tick; update catalog + migrations together).
        return self._path("transcript_inner_tick")

    @property
    def ai_private_md(self) -> str:
        return self._path("ai_private_md")

    @property
    def ai_private_jsonl(self) -> str:
        return self._path("ai_private_jsonl")

    @property
    def context_json(self) -> str:
        return self._path("context_json")

    @property
    def memory_dir(self) -> str:
        return MEMORY_DIR_RELATIVE_PATH

    @property
    def memory_daily_dir(self) -> str:
        return MEMORY_DAILY_DIR_RELATIVE_PATH

    def memory_daily_gist(self, day: str) -> str:
        """Daily gist path; written only by dreaming consolidation."""
        return self._path("memory_daily_gist", day=day)

    @property
    def living_sphere_curator_state_json(self) -> str:
        return self._path("living_sphere_curator_state_json")

    @property
    def context_compaction_state_json(self) -> str:
        return self._path("context_compaction_state_json")

    @property
    def schedule_queue_json(self) -> str:
        return self._path("schedule_queue_json")

    @property
    def dreaming_state_json(self) -> str:
        return self._path("dreaming_state_json")


DEFAULT_MEMORY_STORE_SCOPE_PATHS = MemoryStoreScopePaths()

_REQUIRED_FILES_ATTR = (
    "identity",
    "soul",
    "user_md",
    "memory_md",
    "transcript",
)


def _required_scope_file_relpaths(
    paths: MemoryStoreScopePaths,
) -> tuple[str, ...]:
    return tuple(getattr(paths, attr) for attr in _REQUIRED_FILES_ATTR)


def is_scope_initialized_on_disk(scope_root: Path) -> bool:
    """True when the five-piece exists on disk (prototype REPL only)."""
    root = scope_root.resolve()
    paths = MemoryStoreScopePaths()
    for rel in _required_scope_file_relpaths(paths):
        p = root / rel
        if not p.is_file():
            return False
    return True


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

_CORE_COMPANION_TEMPLATE_ATTRS: tuple[str, ...] = (
    "identity",
    "soul",
    "style_md",
    "user_md",
    "memory_md",
    "channels_md",
)


def ensure_template_seeded_core_documents_in_store(store: MemoryStore) -> None:
    """
    Persist package templates for IDENTITY / SOUL / STYLE / USER / MEMORY when the store has no usable
    body (None or whitespace). Uses MemoryStore.write_document (repository append + cache).
    Does not touch transcript.jsonl; ``ensure_minimal_documents_in_store`` creates an
    empty transcript when the five-piece is not yet satisfied.
    """
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    for attr in _CORE_COMPANION_TEMPLATE_ATTRS:
        rel = getattr(paths, attr)
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


# IDENTITY/USER placeholder markers (Chinese templates).
_IDENTITY_STUB_MARKERS: tuple[str, ...] = (
    "（在此填写",
    "（待定义）",
    "还没定",
    "等你来",
    "待对话填充",
)
_USER_STUB_MARKERS: tuple[str, ...] = (
    "（在此填写",
    "等待你告诉",
    "等待观察",
    "待对话填充",
)


def _text_matches_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    s = text.strip()
    if not s:
        return True
    return any(m in s for m in markers)


def needs_startup_profile_inquiry(store: MemoryStore) -> bool:
    """
    When initialized and transcript has no user/assistant rows yet: if IDENTITY or USER still
    looks like placeholders, the assistant should open the conversation with profile questions.
    """
    from .models import load_transcript_from_store

    if not is_scope_initialized_in_store(store):
        return False
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    rel_tr = paths.transcript
    for m in load_transcript_from_store(store, rel_tr):
        if m.role in ("user", "assistant"):
            return False
    ident = store.read_document_if_exists("IDENTITY.md") or ""
    user_md = store.read_document_if_exists("USER.md") or ""
    id_stub = _text_matches_any_marker(ident, _IDENTITY_STUB_MARKERS)
    user_stub = _text_matches_any_marker(user_md, _USER_STUB_MARKERS)
    out = id_stub or user_stub
    logger.debug(
        "needs_startup_profile_inquiry scope={} id_stub={} user_stub={} -> {}",
        store.scope.registry_key(),
        id_stub,
        user_stub,
        out,
    )
    return out


def companion_scope_pure_relative(relative_path: str) -> PurePosixPath:
    """Return a ``PurePosixPath`` for the normalized scope-relative path (suffix, stem, etc.)."""
    return PurePosixPath(normalize_memory_store_relative_path(relative_path))
