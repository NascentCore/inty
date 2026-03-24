from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChannelType(StrEnum):
    TELEGRAM = "telegram"
    SMS = "sms"
    VOICE_CALL = "voice_call"


class EventDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MemoryType(StrEnum):
    PREFERENCE = "preference"
    RELATIONAL = "relational"
    EPISODIC = "episodic"
    GOAL_PLAN = "goal_plan"


class MemoryStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    STALE = "stale"
    CONFLICTED = "conflicted"


class ActionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


class InteractionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    channel: ChannelType
    direction: EventDirection
    content: str
    timestamp: datetime
    channel_message_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    memory_type: MemoryType
    key: str = Field(min_length=1)
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_event_ids: list[str] = Field(default_factory=list)
    status: MemoryStatus
    first_seen_at: datetime
    last_seen_at: datetime


class PlanAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    scheduled_at: datetime
    preferred_channel: ChannelType
    message_strategy: str = Field(min_length=1)
    constraints: dict[str, Any] = Field(default_factory=dict)
    status: ActionStatus
    result_event_id: str | None = None
