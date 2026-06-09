"""Coordinator and Session."""

from __future__ import annotations

import asyncio
import threading

import pytest

from app.core.companion_harness.runtime.scope import CompanionScope
from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
)
from app.services.agentic_companion.session import (
    Coordinator,
    Session,
)


class _RecordingDownlink:
    def __init__(self) -> None:
        self.events: list[Downlink] = []

    async def deliver(self, event: Downlink) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_presence_coordinator_bootstrap_interim_sink_queues_output() -> None:
    coordinator = Coordinator.for_current_loop()
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
    sink = coordinator.bootstrap_interim_output_sink()
    await sink(ev)
    queued = await coordinator.bootstrap_interim_events.get()
    assert queued == ev


@pytest.mark.asyncio
async def test_presence_coordinator_background_sink_queues_event() -> None:
    coordinator = Coordinator.for_current_loop()
    st = MemoryStore(scope=CompanionScope("u", "a", "c-presence"), repository=None)
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
async def test_presence_coordinator_inner_tick_refresh_preserves_throttle() -> None:
    coordinator = Coordinator.for_current_loop()
    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)
    coordinator.mark_maintenance_inner_tick_fired(123.5, 7)
    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)
    assert coordinator.snapshot_inner_tick_coords() == {
        "user_id": "u1",
        "agent_id": "a1",
        "chat_id": 10,
    }
    assert coordinator.last_maintenance_inner_tick_monotonic() == 123.5
    assert coordinator.last_maintenance_transcript_line_count() == 7


@pytest.mark.asyncio
async def test_presence_coordinator_inner_tick_overlap_flags() -> None:
    coordinator = Coordinator.for_current_loop()
    assert not coordinator.inner_tick_maintenance_foreground_pending()
    assert not coordinator.inner_tick_proactive_tool_bg_still_running()
    ev = threading.Event()
    coordinator.bind_inner_tick_proactive_tool_bg_idle(ev)
    assert coordinator.inner_tick_proactive_tool_bg_still_running()
    ev.set()
    coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
    assert not coordinator.inner_tick_proactive_tool_bg_still_running()
    coordinator.set_foreground_pending(
        "u1", {"ws_inner_tick_maintenance": True, "session_id": "s"}
    )
    assert coordinator.inner_tick_maintenance_foreground_pending()
    coordinator.pop_foreground_pending("u1")
    assert not coordinator.inner_tick_maintenance_foreground_pending()


@pytest.mark.asyncio
async def test_presence_session_deliver_bootstrap_interim() -> None:
    downlink = _RecordingDownlink()
    loop = asyncio.get_running_loop()
    session = Session.create(downlink=downlink, loop=loop)
    interim = BootstrapInterimOutput(
        text="round",
        user_msg_uuid="u",
        trace_id="t",
        langsmith_trace_id="",
        langsmith_run_id="",
        round_index=1,
        had_tool_calls=True,
        assistant_msg_uuid="a",
    )
    await session.deliver_bootstrap_interim(interim)
    assert len(downlink.events) == 1
    assert downlink.events[0].kind is DownlinkKind.BOOTSTRAP_INTERIM
    assert downlink.events[0].bootstrap_interim is interim


@pytest.mark.asyncio
async def test_presence_session_inner_tick_worker_invokes_poll_runner() -> None:
    downlink = _RecordingDownlink()
    loop = asyncio.get_running_loop()
    session = Session.create(downlink=downlink, loop=loop)
    session.store_sign_on_coords(user_id="u1", agent_id="a1", chat_id=10)
    poll_calls: list[dict[str, object]] = []

    async def run_one_poll(snapshot: dict[str, object]) -> None:
        poll_calls.append(snapshot)

    await session.start_inner_tick_worker(poll_seconds=0.05, run_one_poll=run_one_poll)
    await asyncio.sleep(0.12)
    await session.stop()
    assert poll_calls
    assert poll_calls[0] == {"user_id": "u1", "agent_id": "a1", "chat_id": 10}


@pytest.mark.asyncio
async def test_presence_session_sign_out_stops_inner_tick_polls() -> None:
    downlink = _RecordingDownlink()
    loop = asyncio.get_running_loop()
    session = Session.create(downlink=downlink, loop=loop)
    session.store_sign_on_coords(user_id="u1", agent_id="a1", chat_id=10)
    poll_calls: list[dict[str, object]] = []

    async def run_one_poll(snapshot: dict[str, object]) -> None:
        poll_calls.append(snapshot)

    await session.start_inner_tick_worker(poll_seconds=0.05, run_one_poll=run_one_poll)
    await asyncio.sleep(0.07)
    session.sign_out()
    count_after_sign_out = len(poll_calls)
    await asyncio.sleep(0.12)
    await session.stop()
    assert count_after_sign_out == len(poll_calls)


@pytest.mark.asyncio
async def test_presence_session_from_coordinator_reuses_coordinator() -> None:
    downlink = _RecordingDownlink()
    loop = asyncio.get_running_loop()
    coordinator = Coordinator.for_loop(loop)
    session = Session.from_coordinator(
        downlink=downlink,
        coordinator=coordinator,
    )
    assert session.coordinator is coordinator
