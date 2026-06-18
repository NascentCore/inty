"""Serving pipeline data types for Channel, Wire, queues, and AgenticCompanion.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.services.agentic_companion.downlink import DownlinkKind


class QueueStatus(StrEnum):
    """Durable queue row lifecycle."""

    PENDING = "pending"
    CLAIMED = "claimed"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass(frozen=True)
class QueueMessageId:
    """Non-empty durable queue message id."""

    value: str

    def __post_init__(self) -> None:
        assert self.value != ""


@dataclass(frozen=True)
class QueueBatchId:
    """Non-empty batch id grouping input drain or output turn."""

    value: str

    def __post_init__(self) -> None:
        assert self.value != ""


@dataclass(frozen=True)
class WireId:
    """Opaque Channel-owned runtime connection id."""

    value: str

    def __post_init__(self) -> None:
        assert self.value != ""


@dataclass(frozen=True)
class QueueSequence:
    """Monotonic ordering within one AgentScope queue."""

    value: int

    def __post_init__(self) -> None:
        assert self.value >= 0


@dataclass(frozen=True)
class UserMessageBatch:
    """InputQueue batch claimed for one AgenticLoop user-track turn."""

    batch_id: str
    message_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        assert self.batch_id != ""
        assert self.message_ids


class UserInputMessage(BaseModel):
    """One inbound user message appended to InputQueue."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(min_length=1)
    scope: AgentScope
    channel: CompanionRuntimeChannel
    wire_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    received_at_utc: datetime
    client_message_id: str | None = None


class AgentOutputMessage(BaseModel):
    """One agent emission persisted to OutputQueue."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(min_length=1)
    scope: AgentScope
    batch_id: str = Field(min_length=1)
    kind: DownlinkKind
    text: str
    created_at_utc: datetime
    message_ids: tuple[str, ...] = Field(default_factory=tuple)
    trace_id: str | None = None
    langsmith_trace_id: str | None = None
    langsmith_run_id: str | None = None
    turn_recall: str | None = None


class InputQueueRecord(BaseModel):
    """Projection of one input queue DB row."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(min_length=1)
    scope: AgentScope
    sequence: int = Field(ge=0)
    status: QueueStatus
    channel: CompanionRuntimeChannel
    wire_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    received_at_utc: datetime
    client_message_id: str | None = None
    batch_id: str | None = None


class OutputQueueRecord(BaseModel):
    """Projection of one output queue DB row."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(min_length=1)
    scope: AgentScope
    sequence: int = Field(ge=0)
    status: QueueStatus
    batch_id: str = Field(min_length=1)
    kind: DownlinkKind
    text: str
    created_at_utc: datetime
    message_ids: tuple[str, ...] = Field(default_factory=tuple)
    trace_id: str | None = None
    langsmith_trace_id: str | None = None
    langsmith_run_id: str | None = None
    turn_recall: str | None = None
    delivery_channel: CompanionRuntimeChannel | None = None
    delivery_wire_id: str | None = None
    delivery_attempt_count: int = Field(ge=0, default=0)


class AgenticCompanionInputBatch(BaseModel):
    """Claimed pending input messages for one AgenticCompanion drain."""

    model_config = ConfigDict(frozen=True)

    batch_id: str = Field(min_length=1)
    scope: AgentScope
    messages: tuple[InputQueueRecord, ...]
    claimed_at_utc: datetime


@dataclass(frozen=True)
class QueueClaim:
    """One claimed output row awaiting transport delivery."""

    record: OutputQueueRecord
    delivery_channel: CompanionRuntimeChannel
    delivery_wire_id: WireId


@dataclass(frozen=True)
class QueueAck:
    """Successful delivery acknowledgement."""

    message_id: QueueMessageId
    delivered_at_utc: datetime


class AgenticCompanionRunResult(BaseModel):
    """Outcome of one AgenticCompanion drain cycle."""

    model_config = ConfigDict(frozen=True)

    batch_id: str = Field(min_length=1)
    assistant_text: str
    tool_background_started: bool
    output_message_ids: tuple[str, ...] = Field(default_factory=tuple)
    # TODO(!3490): ``input_message_ids`` lets ``ScopeDrainCompletion`` clear legacy
    # ``foreground_pending`` per claimed InputQueue row; drop after queue cleanup.
    input_message_ids: tuple[str, ...]


class TranscriptProjectionRecord(BaseModel):
    """One transcript.jsonl row linked to a queue message."""

    model_config = ConfigDict(frozen=True)

    queue_message_id: str = Field(min_length=1)
    queue_kind: Literal["input", "output"]
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str = Field(min_length=1)
    trace_id: str | None = None
    reply_to: str | None = None


class InboundWireMessage(BaseModel):
    """Channel/Wire boundary payload for one inbound user message."""

    model_config = ConfigDict(frozen=True)

    scope: AgentScope
    channel: CompanionRuntimeChannel
    wire_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    received_at_utc: datetime
    client_message_id: str | None = None


class OutboundWireDelivery(BaseModel):
    """Channel/Wire boundary payload for one outbound assistant message."""

    model_config = ConfigDict(frozen=True)

    record: OutputQueueRecord
    delivery_channel: CompanionRuntimeChannel
    delivery_wire_id: str = Field(min_length=1)


class AgenticLoopInputBatch(BaseModel):
    """Ordered user messages fed into one AgenticLoop user-track turn."""

    model_config = ConfigDict(frozen=True)

    batch_id: str = Field(min_length=1)
    scope: AgentScope
    messages: tuple[InputQueueRecord, ...]
    primary_user_msg_uuid: str = Field(min_length=1)
