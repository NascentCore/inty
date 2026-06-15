"""Process-local scope turn serializer and tool_bg idle keyed by ``CompanionScope.registry_key()``.

TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from .scope import CompanionScope

_REGISTRY_GUARD = threading.Lock()
_SCOPE_TURN_LOCKS: dict[str, ScopeTurnLock] = {}
_SCOPE_TOOL_BG_IDLE: dict[str, threading.Event] = {}


class ScopeTurnLockNotHeldError(RuntimeError):
    """Raised when a lock-gated API runs without the current task holding scope ``turn_lock``."""


class ScopeTurnLock(asyncio.Lock):
    """Per-scope turn serializer that records which asyncio task holds the lock."""

    def __init__(self) -> None:
        super().__init__()
        self._holder_task: asyncio.Task[Any] | None = None

    async def acquire(self) -> bool:
        await super().acquire()
        self._holder_task = asyncio.current_task()
        return True

    def release(self) -> None:
        if self._holder_task is asyncio.current_task():
            self._holder_task = None
        super().release()


def get_scope_turn_lock(scope: CompanionScope) -> ScopeTurnLock:
    """Return the singleton scope turn lock for one ``CompanionScope``."""
    key = scope.registry_key()
    with _REGISTRY_GUARD:
        existing = _SCOPE_TURN_LOCKS.get(key)
        if existing is not None:
            return existing
        lock = ScopeTurnLock()
        _SCOPE_TURN_LOCKS[key] = lock
        return lock


def assert_scope_turn_lock_held_by_current_task(scope: CompanionScope) -> None:
    """Require the running asyncio task to already hold ``scope`` turn lock."""
    lock = get_scope_turn_lock(scope)
    current = asyncio.current_task()
    if current is None:
        raise ScopeTurnLockNotHeldError(
            f"scope turn_lock must be held by an asyncio Task: {scope.registry_key()}"
        )
    if not lock.locked():
        raise ScopeTurnLockNotHeldError(
            f"scope turn_lock is not held: {scope.registry_key()}"
        )
    if lock._holder_task is not current:
        raise ScopeTurnLockNotHeldError(
            f"scope turn_lock is held by another task: {scope.registry_key()}"
        )


def get_scope_tool_bg_idle(scope: CompanionScope) -> threading.Event:
    """Return the singleton ``tool_bg_idle`` event for one companion scope."""
    key = scope.registry_key()
    with _REGISTRY_GUARD:
        existing = _SCOPE_TOOL_BG_IDLE.get(key)
        if existing is not None:
            return existing
        idle_ev = threading.Event()
        idle_ev.set()
        _SCOPE_TOOL_BG_IDLE[key] = idle_ev
        return idle_ev


def release_scope_runtime_state(scope: CompanionScope) -> None:
    """Drop process-local lock and tool_bg_idle for a scope (e.g. MemoryStore shutdown)."""
    key = scope.registry_key()
    with _REGISTRY_GUARD:
        _SCOPE_TURN_LOCKS.pop(key, None)
        _SCOPE_TOOL_BG_IDLE.pop(key, None)


def companion_scope_from_foreground_ctx(
    ctx: dict[str, Any],
) -> CompanionScope | None:
    """Parse ``(user_id, agent_id, chat_id)`` from a tool_bg ``foreground_pending`` ctx."""
    user_id = str(ctx.get("user_id") or "").strip()
    agent_id = str(ctx.get("agent_id") or "").strip()
    chat_id_raw = ctx.get("chat_id")
    if not user_id or not agent_id or chat_id_raw is None:
        return None
    return CompanionScope(
        user_id=user_id,
        companion_id=agent_id,
        chat_id=str(chat_id_raw),
    )
