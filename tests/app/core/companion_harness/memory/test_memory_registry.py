"""Regression: MemoryStore registry is keyed by ``CompanionScope`` only."""

from __future__ import annotations

from app.core.companion_harness.memory.memory_registry import (
    get_memory_store,
    shutdown_all_memory_stores,
    shutdown_memory_store,
)
from app.core.companion_harness.companion.scope import CompanionScope


def test_get_memory_store_same_scope_returns_singleton() -> None:
    try:
        scope = CompanionScope("u1", "a1", "c1")
        dsn = "postgresql://127.0.0.1:5432/none"
        a = get_memory_store(scope, dsn=dsn)
        b = get_memory_store(scope, dsn=dsn)
        assert a is b
        assert a.uses_repository_without_scope_disk is True
    finally:
        shutdown_all_memory_stores()


def test_get_memory_store_different_scopes_distinct_instances() -> None:
    try:
        dsn = "postgresql://127.0.0.1:5432/none"
        s1 = get_memory_store(CompanionScope("u", "a", "chat-1"), dsn=dsn)
        s2 = get_memory_store(CompanionScope("u", "a", "chat-2"), dsn=dsn)
        assert s1 is not s2
    finally:
        shutdown_all_memory_stores()


def test_shutdown_memory_store_evicts_registry_key() -> None:
    try:
        scope = CompanionScope("u2", "a2", "c2")
        dsn = "postgresql://127.0.0.1:5432/none"
        s = get_memory_store(scope, dsn=dsn)
        shutdown_memory_store(scope)
        s2 = get_memory_store(scope, dsn=dsn)
        assert s2 is not s
    finally:
        shutdown_all_memory_stores()
