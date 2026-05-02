"""Provider-agnostic tool calling contracts for agentic kernel.

Covers OpenAI-shaped tool specs and message snapshots (tool_calls on assistant turns),
normalized ToolCall payloads for dispatch, opaque ToolContext for executors, and ToolResult.
Chat roles align with ``contracts.turn.MessageRole``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .turn import MessageRole

ToolRole = MessageRole


class ToolCallSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: str = ""


class ToolMessageSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ToolRole
    content: str = ""
    tool_call_id: str | None = None
    tool_calls: list[ToolCallSnapshot] = Field(default_factory=list)


class ToolSpec(BaseModel):
    """
    Provider-agnostic tool definition.

    `parameters` follows JSON Schema object shape used by OpenAI-compatible tool calling.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments_json: str = ""


class ToolContext(BaseModel):
    """
    Runtime context passed to dispatchers.

    Keep this intentionally generic in Step 0 and enrich in Step 2+.
    """

    model_config = ConfigDict(extra="allow")

    data: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    terminal: bool = False
    artifact_path: str | None = None
