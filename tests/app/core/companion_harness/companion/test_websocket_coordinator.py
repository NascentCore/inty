from __future__ import annotations

import asyncio

import pytest

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
)
from app.core.companion_harness.companion.websocket_coordinator import (
    BootstrapInterimDeliverCtx,
    CompanionWebSocketCoordinator,
)


@pytest.mark.asyncio
async def test_companion_websocket_coordinator_bootstrap_interim_sink_queues_event() -> (
    None
):
    coordinator = CompanionWebSocketCoordinator.for_current_loop()
    ev = BootstrapInterimOutput(
        text="hello before tools",
        user_msg_uuid="user-1",
        trace_id="trace-1",
        langsmith_trace_id="ls-trace",
        langsmith_run_id="ls-run",
        round_index=1,
        had_tool_calls=True,
        assistant_msg_uuid="asst-1",
    )

    coordinator.set_bootstrap_interim_deliver_ctx(
        BootstrapInterimDeliverCtx(
            db=object(),
            agent_id="agent-1",
            session_id="session-1",
            request=object(),
            last_user_text="hi",
            effective_local_id=None,
            outbound_queue=asyncio.Queue(),
        )
    )
    sink = coordinator.bootstrap_interim_output_sink()
    await sink(ev)
    queued = await coordinator.bootstrap_interim_queued_events.get()

    assert queued.ev == ev
    assert queued.ctx is coordinator.bootstrap_interim_deliver_ctx


@pytest.mark.asyncio
async def test_companion_websocket_coordinator_bootstrap_interim_deliver_ctx_lifecycle() -> (
    None
):
    coordinator = CompanionWebSocketCoordinator.for_current_loop()
    outbound_queue: asyncio.Queue[object] = asyncio.Queue()
    ctx = BootstrapInterimDeliverCtx(
        db=object(),
        agent_id="agent-1",
        session_id="session-1",
        request=object(),
        last_user_text="hi",
        effective_local_id=None,
        outbound_queue=outbound_queue,
    )

    coordinator.set_bootstrap_interim_deliver_ctx(ctx)
    assert coordinator.bootstrap_interim_deliver_ctx is ctx
    coordinator.clear_bootstrap_interim_deliver_ctx()
    assert coordinator.bootstrap_interim_deliver_ctx is None


@pytest.mark.asyncio
async def test_companion_websocket_coordinator_background_sink_queues_event() -> (
    None
):
    coordinator = CompanionWebSocketCoordinator.for_current_loop()
    st = MemoryStore(
        scope=CompanionScope("u", "a", "c-ws-coord"), repository=None
    )
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
