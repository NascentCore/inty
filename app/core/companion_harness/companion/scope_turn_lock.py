"""Process-local scope turn serializer keyed by ``CompanionScope.registry_key()``."""

from __future__ import annotations

import asyncio
import threading

from .scope import CompanionScope

_REGISTRY_GUARD = threading.Lock()
_SCOPE_TURN_LOCKS: dict[str, asyncio.Lock] = {}


def get_scope_turn_lock(scope: CompanionScope) -> asyncio.Lock:
    """Return the singleton ``asyncio.Lock`` for one companion scope."""
    key = scope.registry_key()
    with _REGISTRY_GUARD:
        existing = _SCOPE_TURN_LOCKS.get(key)
        if existing is not None:
            return existing
        lock = asyncio.Lock()
        _SCOPE_TURN_LOCKS[key] = lock
        return lock
