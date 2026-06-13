"""Scope-level turn_lock and tool_bg_idle singletons per CompanionScope."""

from __future__ import annotations

import asyncio

import pytest

from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.scope_turn_lock import (
    companion_scope_from_foreground_ctx,
    get_scope_tool_bg_idle,
    get_scope_turn_lock,
    release_scope_runtime_state,
)


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


def test_same_scope_shares_tool_bg_idle_across_sessions() -> None:
    scope = CompanionScope("user-d", "agent-d", "chat-d")
    session_a = _session_stub(scope)
    session_b = _session_stub(scope)
    assert session_a.tool_bg_idle is session_b.tool_bg_idle
    assert session_a.tool_bg_idle is get_scope_tool_bg_idle(scope)
    assert session_a.tool_bg_idle.is_set()


def test_release_scope_runtime_state_evicts_lock_and_idle() -> None:
    scope = CompanionScope("user-e", "agent-e", "chat-e")
    lock_a = get_scope_turn_lock(scope)
    idle_a = get_scope_tool_bg_idle(scope)
    release_scope_runtime_state(scope)
    lock_b = get_scope_turn_lock(scope)
    idle_b = get_scope_tool_bg_idle(scope)
    assert lock_a is not lock_b
    assert idle_a is not idle_b


def test_companion_scope_from_foreground_ctx_parses_coords() -> None:
    scope = companion_scope_from_foreground_ctx(
        {
            "user_id": "u1",
            "agent_id": "a1",
            "chat_id": 42,
        }
    )
    assert scope == CompanionScope("u1", "a1", "42")


def test_companion_scope_from_foreground_ctx_rejects_incomplete() -> None:
    assert companion_scope_from_foreground_ctx({"user_id": "u1"}) is None


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
