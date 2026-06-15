"""``Channel`` ABC and ``RecordingChannel``."""

from __future__ import annotations

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.loop.delivery_policy import (
    DeliveryPolicy,
    TerminalReplyDelivery,
)
from app.core.companion_harness.loop.output_queue import OutputQueue
from app.core.companion_harness.loop.output_queue_types import (
    OutputQueueTranscriptContext,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.services.agentic_companion.channel import RecordingChannel
from app.services.agentic_companion.channel_turn import ChannelTurn
from app.services.agentic_companion.downlink import DownlinkKind
from app.services.agentic_companion.output_queue_delivery import (
    deliver_output_queue,
)


@pytest.mark.asyncio
async def test_recording_channel_delivers_projected_downlink(tmp_path) -> None:
    store = MemoryStore(
        scope=CompanionScope("ch", "a", tmp_path.name),
        repository=None,
    )
    store.write_document("transcript.jsonl", "")
    channel = RecordingChannel()
    queue = OutputQueue(
        transcript_ctx=OutputQueueTranscriptContext(
            store=store,
            transcript_rel="transcript.jsonl",
            user_msg_uuid="u1",
            trace_id="t1",
        ),
        delivery_policy=DeliveryPolicy(
            terminal_reply_delivery=TerminalReplyDelivery.IMMEDIATE
        ),
    )
    delivery = deliver_output_queue(queue, channel)
    await queue.push_user_reply(assistant_text="hi")
    queue.close()
    await delivery
    assert len(channel.events) == 1
    assert channel.events[0].kind is DownlinkKind.USER_REPLY
    assert channel.events[0].assistant_text == "hi"


@pytest.mark.asyncio
async def test_channel_turn_context_manager_drains_on_exit(tmp_path) -> None:
    store = MemoryStore(
        scope=CompanionScope("ct", "a", tmp_path.name),
        repository=None,
    )
    store.write_document("transcript.jsonl", "")
    channel = RecordingChannel()
    async with ChannelTurn.open(
        channel=channel,
        transcript_ctx=OutputQueueTranscriptContext(
            store=store,
            transcript_rel="transcript.jsonl",
            user_msg_uuid="u1",
            trace_id="t1",
        ),
        policy=DeliveryPolicy(
            terminal_reply_delivery=TerminalReplyDelivery.IMMEDIATE
        ),
    ) as queue:
        await queue.push_user_reply(assistant_text="ctx hi")
    assert len(channel.events) == 1
