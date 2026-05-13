"""Process-local MemoryStore registry keyed by ``CompanionScope`` only."""

from __future__ import annotations

import threading

from app.core.companion_harness.memory.memory_store import MemoryStore, SqlAlchemyMemoryRepository
from app.core.companion_harness.memory.scope import CompanionScope

_REGISTRY_LOCK = threading.Lock()
_MEMORY_STORES: dict[str, MemoryStore] = {}


def get_memory_store(scope: CompanionScope, *, dsn: str = "") -> MemoryStore:
    key = scope.registry_key()
    with _REGISTRY_LOCK:
        cur = _MEMORY_STORES.get(key)
        if cur is not None:
            return cur

        repository = None
        if (dsn or "").strip():
            repository = SqlAlchemyMemoryRepository(
                user_id=scope.user_id,
                companion_id=scope.companion_id,
                chat_id=scope.chat_id,
            )

        store = MemoryStore(scope=scope, repository=repository)
        _MEMORY_STORES[key] = store
        return store


def shutdown_memory_store(scope: CompanionScope, *, timeout_s: float = 5.0) -> None:
    key = scope.registry_key()
    store: MemoryStore | None = None
    with _REGISTRY_LOCK:
        store = _MEMORY_STORES.pop(key, None)
    if store is None:
        return
    store.shutdown(timeout_s=timeout_s)


def memory_store_cache_key(scope: CompanionScope) -> str:
    """Stable key for the process-local MemoryStore registry (tests / shutdown / flush)."""
    return scope.registry_key()


def shutdown_all_memory_stores(*, timeout_s: float = 5.0) -> None:
    with _REGISTRY_LOCK:
        items = list(_MEMORY_STORES.values())
        _MEMORY_STORES.clear()
    seen: set[int] = set()
    for store in items:
        sid = id(store)
        if sid in seen:
            continue
        seen.add(sid)
        store.shutdown(timeout_s=timeout_s)
