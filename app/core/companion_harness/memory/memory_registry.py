"""Process-local MemoryStore registry keyed by ``CompanionScope`` only.

TODO(companion-session-eviction): ``_MEMORY_STORES`` grows forever; wire ``shutdown_memory_store`` — #3444
to presence stop / idle TTL eviction (not only tests).
https://github.com/NascentCore/inty/issues/3444
"""

from __future__ import annotations

import threading

from app.core.companion_harness.companion.scope import CompanionScope

from .memory_store import MemoryStore, SqlAlchemyMemoryRepository

_REGISTRY_LOCK = threading.Lock()
_MEMORY_STORES: dict[str, MemoryStore] = {}

MEMORY_STORE_REGISTRY_REQUIRES_DSN = (
    "companion MemoryStore registry requires a non-empty memory_pg_dsn "
    "(configure app.database.url in repo-root config.yaml)."
)


def get_memory_store(scope: CompanionScope, *, dsn: str) -> MemoryStore:
    if not (dsn or "").strip():
        raise ValueError(MEMORY_STORE_REGISTRY_REQUIRES_DSN)
    key = scope.registry_key()
    with _REGISTRY_LOCK:
        cur = _MEMORY_STORES.get(key)
        if cur is not None:
            return cur

        repository = SqlAlchemyMemoryRepository(
            user_id=scope.user_id,
            companion_id=scope.companion_id,
            chat_id=scope.chat_id,
        )

        store = MemoryStore(scope=scope, repository=repository)
        _MEMORY_STORES[key] = store
        return store


def shutdown_memory_store(
    scope: CompanionScope, *, timeout_s: float = 5.0
) -> None:
    key = scope.registry_key()
    store: MemoryStore | None = None
    with _REGISTRY_LOCK:
        store = _MEMORY_STORES.pop(key, None)
    if store is None:
        return
    store.shutdown(timeout_s=timeout_s)
    from app.core.companion_harness.companion.scope_turn_lock import (
        release_scope_runtime_state,
    )
    from app.services.agentic_companion.scope_inner_tick_state import (
        release_scope_inner_tick_state,
    )

    release_scope_runtime_state(scope)
    release_scope_inner_tick_state(scope)


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
