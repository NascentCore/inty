"""Tests for loop sink adapters and output queue projection."""

from __future__ import annotations

import pytest

from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.core.companion_harness.loop.channel_adapter import RecordingChannelAdapter
from app.core.companion_harness.loop.output_queue import AgenticLoopOutputQueue
from app.services.agentic_companion.downlink import DownlinkKind


@pytest.mark.asyncio
async def test_push_bootstrap_interim_delivers_immediately() -> None:
    channel = RecordingChannelAdapter()
    queue = AgenticLoopOutputQueue(channel=channel)
    interim = BootstrapInterimOutput(
        text="interim",
        user_msg_uuid="u1",
        trace_id="t1",
        langsmith_trace_id="ls1",
        langsmith_run_id="lr1",
        round_index=1,
        had_tool_calls=True,
        assistant_msg_uuid="a1",
    )
    await queue.push_bootstrap_interim(interim)
    assert len(channel.events) == 1
    assert channel.events[0].kind == DownlinkKind.BOOTSTRAP_INTERIM
    assert channel.events[0].assistant_text == "interim"
    assert queue.deliverables[0].bootstrap_interim == interim
