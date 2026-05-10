"""Workspace-scoped MemoryStore registry."""

from __future__ import annotations

import threading
from pathlib import Path

from .memory_store import MemoryStore, SqlAlchemyMemoryRepository
from .scope import CompanionScope

_REGISTRY_LOCK = threading.Lock()
_MEMORY_STORES: dict[str, MemoryStore] = {}


def _registry_key(
    workspace_root: Path,
    *,
    user_id: str | None,
    companion_id: str | None,
    chat_id: str | None,
) -> str:
    if user_id is not None and companion_id is not None and chat_id is not None:
        return CompanionScope(user_id, companion_id, chat_id).registry_key()
    return str(workspace_root.resolve())


def _path_registry_alias(workspace_root: Path) -> str:
    return str(workspace_root.resolve())


def _scope_from_workspace_path(workspace_root: Path) -> tuple[str, str, str]:
    p = workspace_root.resolve()
    parts = p.parts
    if len(parts) < 3:
        raise ValueError(
            "Postgres-backed companion MemoryStore requires workspace_root with at least "
            "3 trailing path segments (user_id/companion_id/chat_id). "
            f"Got {p}"
        )
    return parts[-3], parts[-2], parts[-1]


def get_memory_store(
    workspace_root: Path,
    *,
    dsn: str = "",
    user_id: str | None = None,
    companion_id: str | None = None,
    chat_id: str | None = None,
) -> MemoryStore:
    root = workspace_root.resolve()
    key = _registry_key(
        root, user_id=user_id, companion_id=companion_id, chat_id=chat_id
    )
    with _REGISTRY_LOCK:
        cur = _MEMORY_STORES.get(key)
        if cur is not None:
            return cur

        repository = None
        if (dsn or "").strip():
            uid, cid, ck = (
                (user_id, companion_id, chat_id)
                if user_id is not None
                and companion_id is not None
                and chat_id is not None
                else _scope_from_workspace_path(root)
            )
            repository = SqlAlchemyMemoryRepository(
                user_id=uid,
                companion_id=cid,
                chat_id=ck,
            )

        store = MemoryStore(
            workspace_root=root,
            repository=repository,
        )
        _MEMORY_STORES[key] = store
        if repository is not None:
            path_alias = _path_registry_alias(root)
            if path_alias != key:
                _MEMORY_STORES[path_alias] = store
        return store


def _registry_keys_to_evict_for_shutdown(
    workspace_root: Path,
    *,
    user_id: str | None,
    companion_id: str | None,
    chat_id: str | None,
) -> set[str]:
    """All in-process registry keys that may reference the same MemoryStore for this scope."""
    root_r = workspace_root.resolve()
    keys: set[str] = {
        _registry_key(
            root_r,
            user_id=user_id,
            companion_id=companion_id,
            chat_id=chat_id,
        ),
        _path_registry_alias(root_r),
    }
    if len(root_r.parts) >= 3:
        try:
            u, c, ck = _scope_from_workspace_path(root_r)
            keys.add(CompanionScope(u, c, ck).registry_key())
        except ValueError:
            pass
    return keys


def shutdown_memory_store(
    workspace_root: Path,
    *,
    user_id: str | None = None,
    companion_id: str | None = None,
    chat_id: str | None = None,
    timeout_s: float = 5.0,
) -> None:
    root = workspace_root.resolve()
    keys = _registry_keys_to_evict_for_shutdown(
        root,
        user_id=user_id,
        companion_id=companion_id,
        chat_id=chat_id,
    )
    store: MemoryStore | None = None
    with _REGISTRY_LOCK:
        for k in keys:
            got = _MEMORY_STORES.pop(k, None)
            if got is not None:
                store = store or got
    if store is None:
        return
    store.shutdown(timeout_s=timeout_s)


def memory_store_cache_key(
    workspace_root: Path,
    *,
    user_id: str | None = None,
    companion_id: str | None = None,
    chat_id: str | None = None,
) -> str:
    """Stable key for the process-local MemoryStore registry (tests / shutdown / flush)."""
    return _registry_key(
        workspace_root.resolve(),
        user_id=user_id,
        companion_id=companion_id,
        chat_id=chat_id,
    )


def shutdown_all_memory_stores(*, timeout_s: float = 5.0) -> None:
    with _REGISTRY_LOCK:
        items = list(_MEMORY_STORES.items())
        _MEMORY_STORES.clear()
    for _, store in items:
        store.shutdown(timeout_s=timeout_s)
