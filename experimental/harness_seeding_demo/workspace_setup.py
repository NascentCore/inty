"""Prepare a companion MemoryStore scope from seed files before CompanionManager touches it."""

from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.memory.memory_registry import (
    MEMORY_STORE_REGISTRY_REQUIRES_DSN,
    get_memory_store,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.companion.scope import CompanionScope

TEXT_SUFFIXES = frozenset({".md", ".json", ".jsonl"})


def _memory_registry_dsn() -> str:
    url = (global_config_loaded_from_config_yaml.database.url or "").strip()
    if not url:
        raise ValueError(MEMORY_STORE_REGISTRY_REQUIRES_DSN)
    return url


def _iter_seed_files(seed_dir: Path) -> list[Path]:
    return sorted(p for p in seed_dir.iterdir() if p.is_file())


def seed_memory_store_from_directory(seed_dir: Path, scope: CompanionScope) -> None:
    """
    Write each text file from seed_dir into MemoryStore for ``scope``.

    Call this before ``CompanionManager.get_or_create_session`` so
    ``ensure_minimal_documents_in_store`` does not overwrite non-empty seeds.
    """
    sd = seed_dir.resolve()
    if not sd.is_dir():
        raise FileNotFoundError(f"seed directory not found: {sd}")
    store = get_memory_store(scope, dsn=_memory_registry_dsn())
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    for src in _iter_seed_files(sd):
        if src.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = src.name
        body = src.read_text(encoding="utf-8")
        store.write_document(rel, body)
    tr_rel = paths.transcript
    if store.read_document_if_exists(tr_rel) is None:
        store.write_document(tr_rel, "")
