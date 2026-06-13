"""Scope-level turn_lock singleton per CompanionScope."""

from __future__ import annotations

import asyncio

import pytest

from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.scope_turn_lock import get_scope_turn_lock


def _session_stub(scope: CompanionScope) -> CompanionSession:
    return CompanionSession(
        scope=scope,
        store=object(),  # type: ignore[arg-type]
        llm_client=object(),  # type: ignore[arg-type]
        config=object(),  # type: ignore[arg-type]
    )


def test_same_scope_shares_turn_lock_across_sessions() -> None:
    scope = CompanionScope("user-a", "agent-a", "chat-a")
    session_a = _session_stub(scope)
    session_b = _session_stub(scope)
    assert session_a.turn_lock is session_b.turn_lock
    assert session_a.turn_lock is get_scope_turn_lock(scope)


def test_different_scopes_have_distinct_turn_locks() -> None:
    scope_a = CompanionScope("user-a", "agent-a", "chat-a")
    scope_b = CompanionScope("user-b", "agent-b", "chat-b")
    assert get_scope_turn_lock(scope_a) is not get_scope_turn_lock(scope_b)


@pytest.mark.asyncio
async def test_scope_turn_lock_serializes_concurrent_holders() -> None:
    scope = CompanionScope("user-c", "agent-c", "chat-c")
    lock = get_scope_turn_lock(scope)
    order: list[str] = []

    async def holder_a() -> None:
        async with lock:
            order.append("a-enter")
            await asyncio.sleep(0.05)
            order.append("a-exit")

    async def holder_b() -> None:
        await asyncio.sleep(0.01)
        async with lock:
            order.append("b-enter")
            order.append("b-exit")

    await asyncio.gather(holder_a(), holder_b())
    assert order == ["a-enter", "a-exit", "b-enter", "b-exit"]
