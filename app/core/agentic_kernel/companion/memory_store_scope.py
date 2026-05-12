"""MemoryStore scope: synthetic root Path layout, template seeds, and initialization checks."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from loguru import logger

from .file_store import read_text
from .memory_store import MemoryStore

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_PACKAGE_PROMPT_SEED_FILES: Final[frozenset[str]] = frozenset(
    {
        "AXIOM.md",
        "BOOTSTRAP.md",
        "TOOLS.md",
        "SIGNIFICANCE_PERCEPTION.md",
    }
)


def load_template_seed_text(filename: str) -> str:
    base = _PROMPTS_DIR if filename in _PACKAGE_PROMPT_SEED_FILES else _TEMPLATES_DIR
    path = base / filename
    if not path.is_file():
        raise FileNotFoundError(f"missing companion template seed file: {path}")
    return read_text(path).rstrip() + "\n"


@lru_cache(maxsize=1)
def get_imate_axiom_system_text() -> str | None:
    """Product axiom from prompts/AXIOM.md; first system slice for iMate. None if empty."""
    body = load_template_seed_text("AXIOM.md").strip()
    if not body:
        logger.warning("AXIOM.md is empty after strip; skipping axiom system injection")
        return None
    return body


@dataclass(frozen=True)
class MemoryStoreScopePaths:
    """Standard document paths under one synthetic MemoryStore scope root."""

    root: Path
    # State file prefix; prototype uses ".inty_v2" for legacy compatibility.
    state_file_prefix: str = ".companion"

    @property
    def identity(self) -> Path:
        return self.root / "IDENTITY.md"

    @property
    def soul(self) -> Path:
        return self.root / "SOUL.md"

    @property
    def user_md(self) -> Path:
        return self.root / "USER.md"

    @property
    def memory_md(self) -> Path:
        return self.root / "MEMORY.md"

    @property
    def living_sphere_md(self) -> Path:
        return self.root / "LIVING_SPHERE.md"

    @property
    def tools_md(self) -> Path:
        return self.root / "TOOLS.md"

    @property
    def significance_perception_md(self) -> Path:
        return self.root / "SIGNIFICANCE_PERCEPTION.md"

    @property
    def transcript(self) -> Path:
        return self.root / "transcript.jsonl"

    @property
    def transcript_inner_tick(self) -> Path:
        return self.root / "transcript_inner_tick.jsonl"

    @property
    def ai_private_md(self) -> Path:
        return self.root / "ai_private.md"

    @property
    def ai_private_jsonl(self) -> Path:
        return self.root / "ai_private.jsonl"

    @property
    def context_json(self) -> Path:
        return self.root / "context.json"

    @property
    def memory_dir(self) -> Path:
        return self.root / "memory"

    @property
    def memory_daily_dir(self) -> Path:
        return self.memory_dir / "daily"

    def memory_raw_diary(self, day: str) -> Path:
        return self.memory_daily_dir / f"{day}.md"

    def memory_day_summary(self, day: str) -> Path:
        return self.memory_dir / f"{day}.md"

    @property
    def memory_pipeline_state_json(self) -> Path:
        return self.root / f"{self.state_file_prefix}_memory_pipeline.json"

    @property
    def context_compaction_state_json(self) -> Path:
        return self.root / f"{self.state_file_prefix}_context_compaction_state.json"

    @property
    def schedule_queue_json(self) -> Path:
        return self.root / f"{self.state_file_prefix}_schedule_tasks.json"

    @property
    def image_gate_json(self) -> Path:
        return self.root / f"{self.state_file_prefix}_image_gate.json"


_REQUIRED_FILES_ATTR = ("identity", "soul", "user_md", "memory_md", "transcript")


def _required_scope_file_paths(paths: MemoryStoreScopePaths) -> tuple[Path, ...]:
    return tuple(getattr(paths, attr) for attr in _REQUIRED_FILES_ATTR)


def is_scope_initialized_on_disk(scope_root: Path) -> bool:
    """True when the five-piece exists on disk (prototype REPL only)."""
    paths = MemoryStoreScopePaths(root=scope_root.resolve())
    for p in _required_scope_file_paths(paths):
        if not p.is_file():
            return False
    return True


def is_scope_initialized_in_store(scope_root: Path, store: MemoryStore) -> bool:
    """True when the five-piece exists in MemoryStore (production: DB-backed)."""
    root = scope_root.resolve()
    paths = MemoryStoreScopePaths(root=root)
    for attr in _REQUIRED_FILES_ATTR:
        rel = getattr(paths, attr).relative_to(root).as_posix()
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
    "user_md",
    "memory_md",
)


def ensure_template_seeded_core_documents_in_store(
    scope_root: Path,
    store: MemoryStore,
) -> None:
    """
    Persist package templates for IDENTITY / SOUL / USER / MEMORY when the store has no usable
    body (None or whitespace). Uses MemoryStore.write_document (repository append + cache).
    Does not touch transcript.jsonl; ``ensure_minimal_documents_in_store`` creates an
    empty transcript when the five-piece is not yet satisfied.
    """
    root = scope_root.resolve()
    paths = MemoryStoreScopePaths(root=root)
    for attr in _CORE_COMPANION_TEMPLATE_ATTRS:
        rel = getattr(paths, attr).relative_to(root).as_posix()
        body = store.read_document_if_exists(rel)
        if body is None or not body.strip():
            store.write_document(rel, load_template_seed_text(rel))


def ensure_minimal_documents_in_store(
    scope_root: Path,
    store: MemoryStore,
) -> None:
    """Write seed content for required paths into MemoryStore only (no disk authority)."""
    ensure_template_seeded_core_documents_in_store(scope_root, store)
    root = scope_root.resolve()
    if is_scope_initialized_in_store(root, store):
        return
    paths = MemoryStoreScopePaths(root=root)
    for attr in _REQUIRED_FILES_ATTR:
        rel = getattr(paths, attr).relative_to(root).as_posix()
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


def needs_startup_profile_inquiry(
    scope_root: Path,
    store: MemoryStore,
) -> bool:
    """
    When initialized and transcript has no user/assistant rows yet: if IDENTITY or USER still
    looks like placeholders, the assistant should open the conversation with profile questions.
    """
    from .models import load_transcript_from_store

    root = scope_root.resolve()
    if not is_scope_initialized_in_store(root, store):
        return False
    paths = MemoryStoreScopePaths(root=root)
    rel_tr = paths.transcript.relative_to(root).as_posix()
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
        root.name,
        id_stub,
        user_stub,
        out,
    )
    return out


def resolve_under_scope_root(scope_root: Path, relative_path: str) -> Path:
    """
    Resolve a path relative to the synthetic scope root; traversal outside the root is forbidden.
    Empty string means the scope root directory.
    """
    root = scope_root.resolve()
    rel = (relative_path or "").strip().replace("\\", "/")
    if rel.startswith("/"):
        raise ValueError("path must be relative to MemoryStore scope root")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes MemoryStore scope root") from exc
    return candidate
