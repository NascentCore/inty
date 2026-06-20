"""Regression: MemoryStore registry is keyed by ``CompanionScope`` only."""

from __future__ import annotations

import pytest

from app.core.companion_harness.memory.memory_registry import (
    get_memory_store,
    shutdown_all_memory_stores,
    shutdown_memory_store,
)
from app.core.companion_harness.companion.scope import CompanionScope

from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)


def test_get_memory_store_blank_dsn_raises() -> None:
    with pytest.raises(
        ValueError, match="companion MemoryStore registry requires"
    ):
        get_memory_store(CompanionScope("u0", "a0", "c0"), dsn="")


def test_get_memory_store_same_scope_returns_singleton() -> None:
    try:
        scope = CompanionScope("u1", "a1", "c1")
        dsn = companion_memory_registry_dsn()
        a = get_memory_store(scope, dsn=dsn)
        b = get_memory_store(scope, dsn=dsn)
        assert a is b
        assert a.uses_repository_without_scope_disk is True
    finally:
        shutdown_all_memory_stores()


def test_get_memory_store_different_scopes_distinct_instances() -> None:
    try:
        dsn = companion_memory_registry_dsn()
        s1 = get_memory_store(CompanionScope("u", "a", "chat-1"), dsn=dsn)
        s2 = get_memory_store(CompanionScope("u", "a", "chat-2"), dsn=dsn)
        assert s1 is not s2
    finally:
        shutdown_all_memory_stores()


def test_shutdown_memory_store_evicts_registry_key() -> None:
    try:
        scope = CompanionScope("u2", "a2", "c2")
        dsn = companion_memory_registry_dsn()
        s = get_memory_store(scope, dsn=dsn)
        shutdown_memory_store(scope)
        s2 = get_memory_store(scope, dsn=dsn)
        assert s2 is not s
    finally:
        shutdown_all_memory_stores()
