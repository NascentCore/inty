"""Serving pipeline data types for Channel, Wire, queues, and AgenticCompanion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)

AGENT_INITIATED_USER_MESSAGE_BATCH_PREFIX = "agent-initiated:"


class OutputMessageKind(StrEnum):
    """Semantic category of one durable OutputQueue row (not transport encoding)."""

    USER_REPLY = "user_reply"
    # Foreground user-chat reply, or implicit sign-on greeting when track is IMPLICIT_SIGN_ON_GREETING.

    PROACTIVE = "proactive"
    # Inner-tick proactive outreach with synthetic transcript user line.

    MONOLOG = "monolog"
    # Inner-tick monolog; text may be empty on tool-background-only turns.

    SCHEDULED = "scheduled"
    # Due schedule_queue reminder inner-tick.

    TOOL_BACKGROUND = "tool_background"
    # Async tool_background loop produced user-visible assistant text.


class QueueStatus(StrEnum):
    """Durable queue row lifecycle."""

    PENDING = "pending"
    CLAIMED = "claimed"
    DELIVERED = "delivered"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class QueueMessageId:
    """Non-empty durable queue message id."""

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
class UserMessageBatch:
    """InputQueue batch claimed for one AgenticLoop user-track turn."""

    batch_id: str
    message_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        assert self.batch_id != ""
        assert self.message_ids


def synthetic_user_message_batch(
    *,
    user_msg_uuid: str,
    track_label: str,
) -> UserMessageBatch:
    """Build inbound correlation for agent-initiated turns (greeting, inner-tick).

    The ``agent-initiated:`` batch-id prefix marks the output rows as
    agent-initiated for channel routing (see ``output_queue``).
    """
    assert user_msg_uuid != ""
    assert track_label != ""
    return UserMessageBatch(
        batch_id=f"agent-initiated:{track_label}:{user_msg_uuid}",
        message_ids=(user_msg_uuid,),
    )


class UserInputMessage(BaseModel):
    """One inbound user message appended to InputQueue."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(min_length=1)
    scope: AgentScope
    channel: ChannelKind
    wire_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    received_at_utc: datetime
    client_message_id: str | None = None
    local_id: str | None = Field(
        default=None,
        description="Client optimistic-bubble id echoed by App-WS downlink.",
    )
    chat_history_user_row_id: int | None = Field(
        default=None,
        description="Visible-history user row written by App-WS uplink.",
    )


class GeneratedImageRef(BaseModel):
    """Wire-safe generated image metadata emitted with one OutputQueue line."""

    model_config = ConfigDict(frozen=True)

    image_url: str = Field(min_length=1)
    width: int = Field(ge=0, default=0)
    height: int = Field(ge=0, default=0)


class AgentOutputMessage(BaseModel):
    """One agent emission persisted to OutputQueue."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(min_length=1)
    scope: AgentScope
    batch_id: str = Field(min_length=1)
    kind: OutputMessageKind
    text: str
    created_at_utc: datetime
    message_ids: tuple[str, ...] = Field(default_factory=tuple)
    trace_id: str | None = None
    langsmith_trace_id: str | None = None
    langsmith_run_id: str | None = None
    turn_recall: str | None = None
    tool_background_started: bool = False
    generated_images: tuple[GeneratedImageRef, ...] = Field(
        default_factory=tuple
    )


class InputQueueRecord(BaseModel):
    """Projection of one input queue DB row."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(min_length=1)
    scope: AgentScope
    sequence: int = Field(ge=0)
    status: QueueStatus
    channel: ChannelKind
    wire_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    received_at_utc: datetime
    client_message_id: str | None = None
    local_id: str | None = None
    chat_history_user_row_id: int | None = None
    batch_id: str | None = None


class OutputQueueRecord(BaseModel):
    """Projection of one output queue DB row."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(min_length=1)
    scope: AgentScope
    sequence: int = Field(ge=0)
    status: QueueStatus
    batch_id: str = Field(min_length=1)
    kind: OutputMessageKind
    text: str
    created_at_utc: datetime
    message_ids: tuple[str, ...] = Field(default_factory=tuple)
    trace_id: str | None = None
    langsmith_trace_id: str | None = None
    langsmith_run_id: str | None = None
    turn_recall: str | None = None
    tool_background_started: bool = False
    generated_images: tuple[GeneratedImageRef, ...] = Field(
        default_factory=tuple
    )
    delivery_channel: ChannelKind | None = None
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
    delivery_channel: ChannelKind
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


class InboundWireMessage(BaseModel):
    """Channel/Wire boundary payload for one inbound user message."""

    model_config = ConfigDict(frozen=True)

    scope: AgentScope
    channel: ChannelKind
    wire_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    received_at_utc: datetime
    client_message_id: str | None = None
    local_id: str | None = Field(
        default=None,
        description="Client optimistic-bubble id echoed by App-WS downlink.",
    )
    chat_history_user_row_id: int | None = Field(
        default=None,
        description="Visible-history user row written by App-WS uplink.",
    )


class AgenticLoopInputBatch(BaseModel):
    """Ordered user messages fed into one AgenticLoop user-track turn."""

    model_config = ConfigDict(frozen=True)

    batch_id: str = Field(min_length=1)
    scope: AgentScope
    messages: tuple[InputQueueRecord, ...]
    primary_user_msg_uuid: str = Field(min_length=1)
