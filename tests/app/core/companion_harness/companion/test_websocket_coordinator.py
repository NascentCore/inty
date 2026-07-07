from __future__ import annotations


import pytest

from app.core.companion_harness.companion.websocket_coordinator import (
    CompanionWebSocketCoordinator,
)


@pytest.mark.asyncio
async def test_companion_websocket_coordinator_foreground_pending_lifecycle() -> (
    None
):
    coordinator = CompanionWebSocketCoordinator.for_current_loop()

    coordinator.set_foreground_pending("user-msg-1", {"session_id": "s1"})
    assert coordinator.has_foreground_pending("user-msg-1")

    coordinator.update_foreground_pending(
        "user-msg-1", {"foreground_user_message_id": 42}
    )
    assert coordinator.pop_foreground_pending("user-msg-1") == {
        "session_id": "s1",
        "foreground_user_message_id": 42,
    }
    assert coordinator.pop_foreground_pending("user-msg-1") is None


@pytest.mark.asyncio
async def test_companion_websocket_coordinator_inner_tick_refresh_preserves_same_coords_throttle() -> (
    None
):
    coordinator = CompanionWebSocketCoordinator.for_current_loop()

    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)
    coordinator.mark_monolog_inner_tick_fired(123.5, 7)
    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)

    assert coordinator.snapshot_inner_tick_coords() == {
        "user_id": "u1",
        "agent_id": "a1",
        "chat_id": 10,
    }
    assert coordinator.last_monolog_inner_tick_monotonic() == 123.5
    assert coordinator.last_monolog_transcript_line_count() == 7

    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a2", chat_id=10)
    assert coordinator.snapshot_inner_tick_coords() == {
        "user_id": "u1",
        "agent_id": "a2",
        "chat_id": 10,
    }
    assert coordinator.last_monolog_inner_tick_monotonic() is None
    assert coordinator.last_monolog_transcript_line_count() is None


@pytest.mark.asyncio
async def test_companion_websocket_coordinator_clear_inner_tick_coords() -> (
    None
):
    coordinator = CompanionWebSocketCoordinator.for_current_loop()
    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)
    assert coordinator.snapshot_inner_tick_coords() is not None
    coordinator.inner_tick_context.clear()
    assert coordinator.snapshot_inner_tick_coords() is None
