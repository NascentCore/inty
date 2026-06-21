"""Tests for companion turn tail user shaping.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.types import (
    AgenticLoopInputBatch,
    InputQueueRecord,
    QueueStatus,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.companion_harness.companion.scope import CompanionScope
import pytest

from app.core.companion_harness.companion.implicit_signal_messages import (
    USER_SIGNED_ON_TRIGGER_USER_TEXT,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
    append_tail_user_messages_for_llm,
    append_tail_user_transcript_rows,
    resolve_turn_tail_user_messages,
    tail_user_message_contents_for_llm,
)
from app.core.companion_harness.loop.config import (
    BatchUserMessagesLlmCallMode,
)
from app.core.companion_harness.memory.memory_store import MemoryStore


def _record(
    *,
    message_id: str,
    sequence: int,
    text: str,
    ts: datetime,
) -> InputQueueRecord:
    scope = AgentScope(user_id="u1", agent_id="a1")
    return InputQueueRecord(
        message_id=message_id,
        scope=scope,
        sequence=sequence,
        status=QueueStatus.CLAIMED,
        channel=ChannelKind.APP_WS,
        wire_id="wire-1",
        text=text,
        received_at_utc=ts,
    )


def _batch(*records: InputQueueRecord) -> AgenticLoopInputBatch:
    return AgenticLoopInputBatch(
        batch_id="batch-1",
        scope=records[0].scope,
        messages=records,
        primary_user_msg_uuid=records[-1].message_id,
    )


def test_resolve_tail_user_messages_defaults_to_single_fallback() -> None:
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tail = resolve_turn_tail_user_messages(
        mode=BatchUserMessagesLlmCallMode.MULTI_USER_MESSAGES,
        input_batch=None,
        user_text="hello",
        ts_user=ts,
        user_msg_uuid="user-1",
        implicit_sign_on_turn=False,
    )

    assert [(m.message_id, m.text, m.received_at_utc) for m in tail] == [
        ("user-1", "hello", ts)
    ]


def test_resolve_tail_user_messages_joins_batch_for_join_mode() -> None:
    ts1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)
    tail = resolve_turn_tail_user_messages(
        mode=BatchUserMessagesLlmCallMode.JOIN_TO_ONE_USER_MESSAGE,
        input_batch=_batch(
            _record(message_id="m1", sequence=1, text="first", ts=ts1),
            _record(message_id="m2", sequence=2, text="second", ts=ts2),
        ),
        user_text="unused",
        ts_user=ts2,
        user_msg_uuid="m2",
        implicit_sign_on_turn=False,
    )

    assert [(m.message_id, m.text, m.received_at_utc) for m in tail] == [
        ("m2", "first\nsecond", ts2)
    ]


def test_resolve_tail_user_messages_preserves_batch_order_for_multi_mode() -> (
    None
):
    ts1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)
    tail = resolve_turn_tail_user_messages(
        mode=BatchUserMessagesLlmCallMode.MULTI_USER_MESSAGES,
        input_batch=_batch(
            _record(message_id="m1", sequence=1, text="first", ts=ts1),
            _record(message_id="m2", sequence=2, text="second", ts=ts2),
        ),
        user_text="unused",
        ts_user=ts2,
        user_msg_uuid="m2",
        implicit_sign_on_turn=False,
    )

    assert [(m.message_id, m.text, m.received_at_utc) for m in tail] == [
        ("m1", "first", ts1),
        ("m2", "second", ts2),
    ]


def test_append_tail_user_messages_for_llm_appends_separate_user_rows() -> None:
    ts1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)
    messages: list[dict[str, str]] = [{"role": "system", "content": "sys"}]

    append_tail_user_messages_for_llm(
        messages,
        tail_user_messages=(
            TurnTailUserMessage("m1", "first", ts1),
            TurnTailUserMessage("m2", "second", ts2),
        ),
        implicit_sign_on_turn=False,
    )

    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "user",
    ]
    assert "first" in messages[-2]["content"]
    assert "second" in messages[-1]["content"]


def test_implicit_sign_on_multi_batch_crashes_in_llm_tail_without_resolve_guard() -> (
    None
):
    """Documents pre-fix failure: MULTI batch + implicit sign-on hits assert in LLM tail."""
    ts1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)
    tail = resolve_turn_tail_user_messages(
        mode=BatchUserMessagesLlmCallMode.MULTI_USER_MESSAGES,
        input_batch=_batch(
            _record(message_id="m1", sequence=1, text="first", ts=ts1),
            _record(message_id="m2", sequence=2, text="second", ts=ts2),
        ),
        user_text=USER_SIGNED_ON_TRIGGER_USER_TEXT,
        ts_user=ts2,
        user_msg_uuid="m2",
        implicit_sign_on_turn=False,
    )
    assert len(tail) == 2
    with pytest.raises(AssertionError):
        tail_user_message_contents_for_llm(
            tail_user_messages=tail,
            implicit_sign_on_turn=True,
        )


def test_implicit_sign_on_multi_batch_rejected_at_resolve() -> None:
    ts1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)
    with pytest.raises(AssertionError):
        resolve_turn_tail_user_messages(
            mode=BatchUserMessagesLlmCallMode.MULTI_USER_MESSAGES,
            input_batch=_batch(
                _record(message_id="m1", sequence=1, text="first", ts=ts1),
                _record(message_id="m2", sequence=2, text="second", ts=ts2),
            ),
            user_text=USER_SIGNED_ON_TRIGGER_USER_TEXT,
            ts_user=ts2,
            user_msg_uuid="m2",
            implicit_sign_on_turn=True,
        )


def test_implicit_sign_on_single_batch_tail_yields_one_llm_content() -> None:
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tail = resolve_turn_tail_user_messages(
        mode=BatchUserMessagesLlmCallMode.MULTI_USER_MESSAGES,
        input_batch=_batch(
            _record(message_id="m1", sequence=1, text="hello", ts=ts),
        ),
        user_text=USER_SIGNED_ON_TRIGGER_USER_TEXT,
        ts_user=ts,
        user_msg_uuid="m1",
        implicit_sign_on_turn=True,
    )
    contents = tail_user_message_contents_for_llm(
        tail_user_messages=tail,
        implicit_sign_on_turn=True,
    )
    assert len(contents) == 1
    assert USER_SIGNED_ON_TRIGGER_USER_TEXT in contents[0]


def test_append_tail_user_transcript_rows_persists_each_user_message() -> None:
    ts1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)
    store = MemoryStore(
        scope=CompanionScope("user-1", "agent-1", "chat-1"),
        repository=None,
    )

    append_tail_user_transcript_rows(
        store,
        "transcript.jsonl",
        tail_user_messages=(
            TurnTailUserMessage("m1", "first", ts1),
            TurnTailUserMessage("m2", "second", ts2),
        ),
        trace_id="trace-1",
    )

    raw = store.read_document_if_exists("transcript.jsonl")
    assert raw is not None
    rows = [json.loads(line) for line in raw.splitlines()]
    assert [(row["uuid"], row["content"], row["ts"]) for row in rows] == [
        ("m1", "first", ts1.isoformat()),
        ("m2", "second", ts2.isoformat()),
    ]
