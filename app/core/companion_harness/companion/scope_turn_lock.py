"""Process-local scope turn serializer and tool_bg idle keyed by ``CompanionScope.registry_key()``."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from .scope import CompanionScope

_REGISTRY_GUARD = threading.Lock()
_SCOPE_TURN_LOCKS: dict[str, asyncio.Lock] = {}
_SCOPE_TOOL_BG_IDLE: dict[str, threading.Event] = {}


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


def companion_scope_from_foreground_ctx(ctx: dict[str, Any]) -> CompanionScope | None:
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
