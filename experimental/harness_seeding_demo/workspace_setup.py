"""Prepare a companion workspace from seed files before CompanionManager touches it."""

from __future__ import annotations

from pathlib import Path

from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.workspace import WorkspacePaths

TEXT_SUFFIXES = frozenset({".md", ".json", ".jsonl"})


def _iter_seed_files(seed_dir: Path) -> list[Path]:
    return sorted(p for p in seed_dir.iterdir() if p.is_file())


def seed_memory_store_from_directory(seed_dir: Path, workspace_root: Path) -> None:
    """
    Write each text file from seed_dir into MemoryStore for workspace_root.

    Call this before CompanionManager.get_or_create_session so
    ensure_minimal_workspace_documents_in_store does not overwrite non-empty seeds.
    """
    root = workspace_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    store = get_memory_store(root, dsn="")
    paths = WorkspacePaths(root=root)
    for src in _iter_seed_files(seed_dir.resolve()):
        if src.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = src.name
        body = src.read_text(encoding="utf-8")
        store.write_document(rel, body)
    tr_rel = paths.transcript.relative_to(root).as_posix()
    if store.read_document_if_exists(tr_rel) is None:
        store.write_document(tr_rel, "")
