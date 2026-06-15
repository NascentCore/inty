"""``DeliveryPolicy`` defers bootstrap terminal ``USER_REPLY`` until queue close."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
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
from app.services.agentic_companion.downlink import DownlinkKind
from app.services.agentic_companion.output_queue_delivery import (
    deliver_output_queue,
)


@pytest.mark.asyncio
async def test_defer_terminal_user_reply_until_queue_close(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("defer", "a", tmp_path.name),
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
            terminal_reply_delivery=TerminalReplyDelivery.ON_QUEUE_CLOSE
        ),
    )
    delivery = asyncio.create_task(deliver_output_queue(queue, channel))
    await queue.push_interim_reply(
        BootstrapInterimOutput(
            text="interim body",
            user_msg_uuid="u1",
            trace_id="t1",
            langsmith_trace_id="",
            langsmith_run_id="",
            round_index=1,
            had_tool_calls=True,
            assistant_msg_uuid="i1",
        )
    )
    await asyncio.sleep(0)
    assert len(channel.events) == 1
    assert channel.events[0].kind is DownlinkKind.BOOTSTRAP_INTERIM
    await queue.push_user_reply(assistant_text="terminal")
    await asyncio.sleep(0)
    assert len(channel.events) == 1
    queue.close()
    await delivery
    assert len(channel.events) == 2
    assert channel.events[1].kind is DownlinkKind.USER_REPLY
    assert channel.events[1].assistant_text == "terminal"
