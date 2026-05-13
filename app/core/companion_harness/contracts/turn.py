"""Core turn-level runtime contracts for Companion Harness."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MessageRole = Literal["system", "user", "assistant", "tool"]


class MessageSnapshot(BaseModel):
    """Normalized message record shared by orchestrator and providers."""

    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: str = ""
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnInput(BaseModel):
    """Minimal turn input used by runtime orchestrator."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    user_text: str = Field(min_length=1)
    history: list[MessageSnapshot] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnOutput(BaseModel):
    """Minimal turn output produced by runtime orchestrator."""

    model_config = ConfigDict(extra="forbid")

    assistant_text: str = ""
    emitted_messages: list[MessageSnapshot] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
