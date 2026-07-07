"""Bootstrap interim output sinks for AgenticLoop tool rounds.

Typed callbacks for delivering in-turn assistant text before a turn completes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

BackgroundToolEventSink = Callable[["ToolOutputEvent"], None]


# TODO(#3402): Replace with channel-agnostic ``UserVisibleChunk`` + ``UserVisibleChunkSink``.
class BootstrapInterimOutput(BaseModel):
    """One bootstrap sync tool-loop LLM round delivered to the client before turn end."""

    model_config = ConfigDict(extra="forbid")

    text: str
    user_msg_uuid: str
    trace_id: str
    langsmith_trace_id: str
    langsmith_run_id: str
    round_index: int
    had_tool_calls: bool
    assistant_msg_uuid: str


BootstrapInterimOutputSink = Callable[[BootstrapInterimOutput], Awaitable[None]]
