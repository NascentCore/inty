"""Transcript-on-enqueue for ``OutputQueue`` deliverables."""

from __future__ import annotations

import json
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
from app.core.companion_harness.tools.tool_background import ToolOutputEvent


def _store(tmp_path: Path) -> MemoryStore:
    store = MemoryStore(
        scope=CompanionScope("oq-transcript", "agent", tmp_path.name),
        repository=None,
    )
    store.write_document("transcript.jsonl", "")
    return store


def _queue(store: MemoryStore) -> OutputQueue:
    return OutputQueue(
        transcript_ctx=OutputQueueTranscriptContext(
            store=store,
            transcript_rel="transcript.jsonl",
            user_msg_uuid="user-1",
            trace_id="trace-1",
        ),
        delivery_policy=DeliveryPolicy(
            terminal_reply_delivery=TerminalReplyDelivery.IMMEDIATE
        ),
    )


@pytest.mark.asyncio
async def test_enqueue_user_reply_writes_transcript_row(tmp_path: Path) -> None:
    store = _store(tmp_path)
    queue = _queue(store)
    await queue.push_user_reply(assistant_text="hello user")
    raw = json.loads(store.read_document("transcript.jsonl").strip())
    assert raw["role"] == "assistant"
    assert raw["content"] == "hello user"
    assert raw["reply_to"] == "user-1"
    assert raw["trace_id"] == "trace-1"
    assert raw["source"] == "chat"
    assert "tool_results_digest" not in raw


@pytest.mark.asyncio
async def test_enqueue_interim_uses_interim_assistant_uuid(tmp_path: Path) -> None:
    store = _store(tmp_path)
    queue = _queue(store)
    await queue.push_interim_reply(
        BootstrapInterimOutput(
            text="interim",
            user_msg_uuid="user-1",
            trace_id="trace-1",
            langsmith_trace_id="",
            langsmith_run_id="",
            round_index=1,
            had_tool_calls=True,
            assistant_msg_uuid="interim-a1",
        )
    )
    raw = json.loads(store.read_document("transcript.jsonl").strip())
    assert raw["content"] == "interim"
    assert raw["uuid"] == "interim-a1"


@pytest.mark.asyncio
async def test_enqueue_tool_background_splits_display_and_digest(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    queue = _queue(store)
    event = ToolOutputEvent(
        scope_registry_key="scope",
        memory_store=store,
        user_msg_uuid="user-1",
        assistant_msg_uuid="bg-a1",
        text="Routing line",
        ts="2026-01-01T00:00:00+00:00",
        elapsed_ms=10,
        trace_id="trace-1",
        tool_results_digest="tool_ok",
    )
    await queue.push_tool_background(event)
    raw = json.loads(store.read_document("transcript.jsonl").strip())
    assert raw["content"] == "Routing line"
    assert raw["source"] == "tool_bg"
    assert raw["tool_results_digest"] == {"body": "tool_ok"}


@pytest.mark.asyncio
async def test_enqueue_does_not_deliver_on_channel(tmp_path: Path) -> None:
    store = _store(tmp_path)
    queue = _queue(store)
    await queue.push_user_reply(assistant_text="only transcript")
    assert len(queue.deliverables) == 1
    queue.close()
    item = await queue.pull()
    from app.core.companion_harness.loop.output_queue import QUEUE_CLOSED

    assert item is not QUEUE_CLOSED
    assert item.assistant_text == "only transcript"  # type: ignore[union-attr]
    assert await queue.pull() is QUEUE_CLOSED
