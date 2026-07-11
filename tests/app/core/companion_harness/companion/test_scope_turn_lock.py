"""Scope-level turn_lock and tool_bg_idle singletons per CompanionScope."""

from __future__ import annotations

import asyncio

import pytest

from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.scope_turn_lock import (
    ScopeTurnLockNotHeldError,
    assert_scope_turn_lock_held_by_current_task,
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


@pytest.mark.asyncio
async def test_assert_scope_turn_lock_held_by_current_task_requires_holder() -> (
    None
):
    scope = CompanionScope("user-f", "agent-f", "chat-f")
    with pytest.raises(ScopeTurnLockNotHeldError, match="is not held"):
        assert_scope_turn_lock_held_by_current_task(scope)
    lock = get_scope_turn_lock(scope)
    async with lock:
        assert_scope_turn_lock_held_by_current_task(scope)


@pytest.mark.asyncio
async def test_scope_turn_lock_release_rejects_non_holder() -> None:
    scope = CompanionScope("user-h", "agent-h", "chat-h")
    lock = get_scope_turn_lock(scope)
    holder_ready = asyncio.Event()
    holder_done = asyncio.Event()

    async def holder() -> None:
        await lock.acquire()
        holder_ready.set()
        await holder_done.wait()
        lock.release()

    holder_task = asyncio.create_task(holder())
    await holder_ready.wait()
    assert lock.locked()
    assert lock._holder_task is holder_task
    with pytest.raises(ScopeTurnLockNotHeldError, match="another task"):
        lock.release()
    assert lock.locked()
    assert lock._holder_task is holder_task
    holder_done.set()
    await holder_task


@pytest.mark.asyncio
async def test_assert_scope_turn_lock_rejects_other_task_holder() -> None:
    scope = CompanionScope("user-g", "agent-g", "chat-g")
    lock = get_scope_turn_lock(scope)
    ready = asyncio.Event()
    release = asyncio.Event()

    async def holder() -> None:
        async with lock:
            ready.set()
            await release.wait()

    task = asyncio.create_task(holder())
    await ready.wait()
    with pytest.raises(ScopeTurnLockNotHeldError, match="another task"):
        assert_scope_turn_lock_held_by_current_task(scope)
    release.set()
    await task
