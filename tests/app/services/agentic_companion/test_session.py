"""Coordinator and Session."""

from __future__ import annotations

import asyncio
import threading

import pytest

from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
)
from app.services.agentic_companion.session import (
    Coordinator,
    Session,
)


class _RecordingDownlink:
    def __init__(self) -> None:
        self.messages: list[ReadyOutputMessage] = []

    async def deliver(self, message: ReadyOutputMessage) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
async def test_presence_coordinator_inner_tick_refresh_preserves_throttle() -> (
    None
):
    coordinator = Coordinator.for_current_loop()
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


@pytest.mark.asyncio
async def test_presence_coordinator_inner_tick_overlap_flags() -> None:
    coordinator = Coordinator.for_current_loop()
    assert not coordinator.inner_tick_proactive_tool_bg_still_running()
    ev = threading.Event()
    coordinator.bind_inner_tick_proactive_tool_bg_idle(ev)
    assert coordinator.inner_tick_proactive_tool_bg_still_running()
    ev.set()
    coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
    assert not coordinator.inner_tick_proactive_tool_bg_still_running()


@pytest.mark.asyncio
async def test_presence_coordinator_autonomy_throttle_and_overlap_flags() -> (
    None
):
    coordinator = Coordinator.for_current_loop()
    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)
    assert coordinator.last_autonomy_inner_tick_monotonic() is None
    assert coordinator.last_autonomy_transcript_line_count() is None
    assert not coordinator.inner_tick_autonomy_tool_bg_still_running()
    coordinator.mark_autonomy_inner_tick_fired(222.5, 11)
    assert coordinator.last_autonomy_inner_tick_monotonic() == 222.5
    assert coordinator.last_autonomy_transcript_line_count() == 11
    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)
    assert coordinator.last_autonomy_inner_tick_monotonic() == 222.5
    assert coordinator.last_autonomy_transcript_line_count() == 11
    coordinator.store_inner_tick_coords(user_id="u2", agent_id="a1", chat_id=10)
    assert coordinator.last_autonomy_inner_tick_monotonic() is None
    assert coordinator.last_autonomy_transcript_line_count() is None
    ev = threading.Event()
    coordinator.bind_inner_tick_autonomy_tool_bg_idle(ev)
    assert coordinator.inner_tick_autonomy_tool_bg_still_running()
    ev.set()
    coordinator.clear_inner_tick_autonomy_tool_bg_idle_if_idle()
    assert not coordinator.inner_tick_autonomy_tool_bg_still_running()


@pytest.mark.asyncio
async def test_presence_session_inner_tick_worker_runs_poll() -> None:
    downlink = _RecordingDownlink()
    loop = asyncio.get_running_loop()
    session = Session.create(downlink=downlink, loop=loop)
    poll_calls: list[dict] = []

    async def _run_poll(ctx: dict) -> None:
        poll_calls.append(dict(ctx))

    session.store_sign_on_coords(user_id="u1", agent_id="a1", chat_id=10)
    await session.start_inner_tick_worker(
        poll_seconds=0.05, run_one_poll=_run_poll
    )
    await asyncio.sleep(0.12)
    count_after_sign_out = len(poll_calls)
    session.sign_out()
    await asyncio.sleep(0.12)
    assert count_after_sign_out == len(poll_calls)
    await session.stop()


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
