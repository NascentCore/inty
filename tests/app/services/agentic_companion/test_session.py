"""Coordinator and Session."""

from __future__ import annotations

import asyncio

import pytest

from app.core.agentic_companion.output_queue import (
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
async def test_presence_coordinator_inner_tick_refresh_preserves_coords() -> (
    None
):
    coordinator = Coordinator.for_current_loop()
    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)
    coordinator.store_inner_tick_coords(user_id="u1", agent_id="a1", chat_id=10)
    assert coordinator.snapshot_inner_tick_coords() == {
        "user_id": "u1",
        "agent_id": "a1",
        "chat_id": 10,
    }


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
    assert count_after_sign_out >= 1
    await session.stop()
