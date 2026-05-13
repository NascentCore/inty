from __future__ import annotations

import pytest

from app.core.companion_harness.companion.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.tool_background import ToolOutputEvent
from app.core.companion_harness.companion.websocket_coordinator import (
    CompanionWebSocketCoordinator,
)


@pytest.mark.asyncio
async def test_companion_websocket_coordinator_background_sink_queues_event() -> None:
    coordinator = CompanionWebSocketCoordinator.for_current_loop()
    st = MemoryStore(scope=CompanionScope("u", "a", "c-ws-coord"), repository=None)
    event = ToolOutputEvent(
        scope_registry_key=st.scope.registry_key(),
        memory_store=st,
        user_msg_uuid="user-msg-1",
        assistant_msg_uuid="assistant-msg-1",
        text="visible tool result",
        ts="2026-05-10T00:00:00Z",
        elapsed_ms=7,
    )

    coordinator.background_sink(event)
    queued = await coordinator.background_events.get()

    assert queued is event


@pytest.mark.asyncio
async def test_companion_websocket_coordinator_foreground_pending_lifecycle() -> None:
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
async def test_companion_websocket_coordinator_heartbeat_refresh_preserves_same_coords_throttle() -> None:
    coordinator = CompanionWebSocketCoordinator.for_current_loop()

    coordinator.store_heartbeat_coords(user_id="u1", agent_id="a1", chat_id=10)
    coordinator.mark_maintenance_inner_tick_fired(123.5)
    coordinator.store_heartbeat_coords(user_id="u1", agent_id="a1", chat_id=10)

    assert coordinator.snapshot_heartbeat_coords() == {
        "user_id": "u1",
        "agent_id": "a1",
        "chat_id": 10,
    }
    assert coordinator.last_maintenance_inner_tick_monotonic() == 123.5

    coordinator.store_heartbeat_coords(user_id="u1", agent_id="a2", chat_id=10)
    assert coordinator.snapshot_heartbeat_coords() == {
        "user_id": "u1",
        "agent_id": "a2",
        "chat_id": 10,
    }
    assert coordinator.last_maintenance_inner_tick_monotonic() is None
