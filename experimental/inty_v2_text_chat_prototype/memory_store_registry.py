"""Prototype adapter: reads env vars, delegates to kernel memory_registry."""

from __future__ import annotations

import os
from pathlib import Path

from app.core.agentic_kernel.companion.memory_registry import (
    get_memory_store as _kernel_get,
    shutdown_all_memory_stores,  # noqa: F401
    shutdown_memory_store,  # noqa: F401
)
from app.core.agentic_kernel.companion.memory_store import MemoryStore


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


def get_memory_store(workspace_root: Path) -> MemoryStore:
    dsn = (os.getenv("INTY_V2_PROTO_MEMORY_PG_DSN") or "").strip()
    table_name = (
        os.getenv(
            "INTY_V2_PROTO_MEMORY_PG_TABLE",
            "proto_memory_doc_versions",
        ).strip()
        or "proto_memory_doc_versions"
    )
    mirror = _env_bool("INTY_V2_PROTO_MEMORY_MIRROR_TO_FILES", default=True)
    return _kernel_get(
        workspace_root,
        dsn=dsn,
        table_name=table_name,
        mirror_to_files=mirror,
    )


def flush_memory_store(workspace_root: Path, *, timeout_s: float = 5.0) -> None:
    root = workspace_root.resolve()
    from app.core.agentic_kernel.companion.memory_registry import (
        _REGISTRY_LOCK,
        _MEMORY_STORES,
    )

    with _REGISTRY_LOCK:
        store = _MEMORY_STORES.get(str(root))
    if store is None:
        return
    store.flush_now(timeout_s=timeout_s)
