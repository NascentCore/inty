"""Tests for agentic companion serving pipeline types."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.types import (
    AgenticCompanionInputBatch,
    InboundWireMessage,
    InputQueueRecord,
    QueueBatchId,
    QueueMessageId,
    QueueStatus,
    UserMessageBatch,
    WireId,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)


def test_queue_message_id_rejects_empty() -> None:
    with pytest.raises(AssertionError):
        QueueMessageId("")


def test_inbound_wire_message_fields() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    inbound = InboundWireMessage(
        scope=scope,
        channel=CompanionRuntimeChannel.TELEGRAM,
        wire_id="wire-1",
        text="hello",
        received_at_utc=datetime.now(UTC),
    )
    assert inbound.scope.user_id == "u1"
    assert inbound.text == "hello"


def test_input_batch_preserves_order() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    now = datetime.now(UTC)
    records = (
        InputQueueRecord(
            message_id="m1",
            scope=scope,
            sequence=1,
            status=QueueStatus.CLAIMED,
            channel=CompanionRuntimeChannel.TELEGRAM,
            wire_id="w1",
            text="a",
            received_at_utc=now,
        ),
        InputQueueRecord(
            message_id="m2",
            scope=scope,
            sequence=2,
            status=QueueStatus.CLAIMED,
            channel=CompanionRuntimeChannel.TELEGRAM,
            wire_id="w1",
            text="b",
            received_at_utc=now,
        ),
    )
    batch = AgenticCompanionInputBatch(
        batch_id="b1",
        scope=scope,
        messages=records,
        claimed_at_utc=now,
    )
    assert QueueBatchId("b1").value == batch.batch_id
    assert WireId("w1").value == records[0].wire_id
    assert [m.text for m in batch.messages] == ["a", "b"]


def test_user_message_batch_requires_non_empty_ids() -> None:
    batch = UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))
    assert batch.batch_id == "batch-1"
    assert batch.message_ids == ("input-1",)
    with pytest.raises(AssertionError):
        UserMessageBatch(batch_id="", message_ids=("input-1",))
    with pytest.raises(AssertionError):
        UserMessageBatch(batch_id="batch-1", message_ids=())
