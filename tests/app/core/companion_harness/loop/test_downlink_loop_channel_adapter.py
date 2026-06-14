"""DownlinkLoopChannelAdapter forwards to inner channel."""

from __future__ import annotations

import pytest

from app.core.companion_harness.loop.channel_adapter import DownlinkLoopChannelAdapter
from app.services.agentic_companion.downlink import Downlink, DownlinkKind


class _RecordingInner:
    def __init__(self) -> None:
        self.events: list[Downlink] = []

    async def deliver(self, event: Downlink) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_downlink_loop_channel_adapter_forwards() -> None:
    inner = _RecordingInner()
    adapter = DownlinkLoopChannelAdapter(inner)
    event = Downlink(
        kind=DownlinkKind.BOOTSTRAP_INTERIM,
        assistant_text="x",
        turn=None,
        tool_output=None,
        bootstrap_interim=None,
        scheduled_task_id=None,
        transcript_user_text=None,
    )
    await adapter.deliver(event)
    assert inner.events == [event]
