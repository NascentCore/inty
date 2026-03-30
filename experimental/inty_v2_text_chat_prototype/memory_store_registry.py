"""Workspace-scoped MemoryStore registry."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from .memory_store import MemoryStore, PostgresMemoryRepository

_REGISTRY_LOCK = threading.Lock()
_MEMORY_STORES: dict[str, MemoryStore] = {}


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    s = raw.strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"{name} must be a boolean-like value, got {raw!r}")


def _env_positive_int(name: str, *, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        n = int(raw.strip(), 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}") from exc
    if n < 1:
        raise ValueError(f"{name} must be >= 1, got {n}")
    return n


def get_memory_store(workspace_root: Path) -> MemoryStore:
    root = workspace_root.resolve()
    key = str(root)
    with _REGISTRY_LOCK:
        cur = _MEMORY_STORES.get(key)
        if cur is not None:
            return cur

        dsn = (os.getenv("INTY_V2_PROTO_MEMORY_PG_DSN") or "").strip()
        table_name = (
            os.getenv("INTY_V2_PROTO_MEMORY_PG_TABLE", "proto_memory_docs").strip()
            or "proto_memory_docs"
        )
        repository = None
        if dsn:
            repo = PostgresMemoryRepository(dsn=dsn, table_name=table_name)
            repo.ensure_schema()
            repository = repo

        store = MemoryStore(
            workspace_root=root,
            repository=repository,
            mirror_to_files=_env_bool(
                "INTY_V2_PROTO_MEMORY_MIRROR_TO_FILES",
                default=True,
            ),
            flush_batch_size=_env_positive_int(
                "INTY_V2_PROTO_MEMORY_FLUSH_BATCH_SIZE",
                default=64,
            ),
        )
        _MEMORY_STORES[key] = store
        return store


def flush_memory_store(workspace_root: Path, *, timeout_s: float = 5.0) -> None:
    root = workspace_root.resolve()
    with _REGISTRY_LOCK:
        store = _MEMORY_STORES.get(str(root))
    if store is None:
        return
    store.flush_now(timeout_s=timeout_s)


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
