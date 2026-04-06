"""Workspace-scoped MemoryStore registry."""

from __future__ import annotations

import threading
from pathlib import Path

from .memory_store import MemoryStore, PostgresMemoryRepository

_REGISTRY_LOCK = threading.Lock()
_MEMORY_STORES: dict[str, MemoryStore] = {}


def get_memory_store(
    workspace_root: Path,
    *,
    dsn: str = "",
    table_name: str = "companion_memory_doc_versions",
    mirror_to_files: bool = True,
    allow_workspace_disk_fallback: bool = True,
) -> MemoryStore:
    root = workspace_root.resolve()
    key = str(root)
    with _REGISTRY_LOCK:
        cur = _MEMORY_STORES.get(key)
        if cur is not None:
            return cur

        repository = None
        if dsn:
            repo = PostgresMemoryRepository(dsn=dsn, table_name=table_name)
            repo.ensure_schema()
            repository = repo

        store = MemoryStore(
            workspace_root=root,
            repository=repository,
            mirror_to_files=mirror_to_files,
            allow_workspace_disk_fallback=allow_workspace_disk_fallback,
        )
        _MEMORY_STORES[key] = store
        return store


def shutdown_memory_store(workspace_root: Path, *, timeout_s: float = 5.0) -> None:
    root = workspace_root.resolve()
    with _REGISTRY_LOCK:
        store = _MEMORY_STORES.pop(str(root), None)
    if store is None:
        return
    store.shutdown(timeout_s=timeout_s)


def shutdown_all_memory_stores(*, timeout_s: float = 5.0) -> None:
    with _REGISTRY_LOCK:
        items = list(_MEMORY_STORES.items())
        _MEMORY_STORES.clear()
    for _, store in items:
        store.shutdown(timeout_s=timeout_s)
