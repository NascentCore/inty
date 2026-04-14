"""Prototype adapter: reads env vars, delegates to kernel memory_registry."""

from __future__ import annotations

import os
from pathlib import Path

from app.core.agentic_kernel.companion.memory_registry import (
    get_memory_store as _kernel_get,
    memory_store_cache_key,
    shutdown_all_memory_stores,  # noqa: F401
    shutdown_memory_store,  # noqa: F401
)
from app.core.agentic_kernel.companion.memory_store import MemoryStore


def get_memory_store(workspace_root: Path) -> MemoryStore:
    dsn = (os.getenv("INTY_V2_PROTO_MEMORY_PG_DSN") or "").strip()
    return _kernel_get(workspace_root, dsn=dsn)


def flush_memory_store(workspace_root: Path, *, timeout_s: float = 5.0) -> None:
    root = workspace_root.resolve()
    from app.core.agentic_kernel.companion.memory_registry import (
        _REGISTRY_LOCK,
        _MEMORY_STORES,
    )

    with _REGISTRY_LOCK:
        store = _MEMORY_STORES.get(memory_store_cache_key(root))
    if store is None:
        return
    store.flush_now(timeout_s=timeout_s)
