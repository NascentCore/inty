"""Process-wide registry of companion scopes that currently have a live presence.

A "presence" is a signed-on WebSocket or in-process Weixin binding whose
inner-tick worker already drives maintenance for its ``(user, agent, chat)``
scope. The offline maintenance scheduler consults this registry to skip such
scopes, so the same MemoryStore is never driven by two maintenance turns at
once. Reference-counted to tolerate multiple concurrent presences per scope.
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_present_counts: dict[str, int] = {}


def mark_present(scope_key: str) -> None:
    """Record one more live presence for ``scope_key`` (CompanionScope.registry_key)."""
    assert scope_key, "scope_key must be non-empty"
    with _lock:
        _present_counts[scope_key] = _present_counts.get(scope_key, 0) + 1


def clear_present(scope_key: str) -> None:
    """Drop one live presence for ``scope_key``; removes the entry at zero."""
    assert scope_key, "scope_key must be non-empty"
    with _lock:
        remaining = _present_counts.get(scope_key, 0) - 1
        if remaining > 0:
            _present_counts[scope_key] = remaining
        else:
            _present_counts.pop(scope_key, None)


def is_present(scope_key: str) -> bool:
    """True when at least one live presence holds ``scope_key``."""
    assert scope_key, "scope_key must be non-empty"
    with _lock:
        return _present_counts.get(scope_key, 0) > 0
