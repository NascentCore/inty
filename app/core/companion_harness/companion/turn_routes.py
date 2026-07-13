"""In-turn interim output payload for AgenticLoop tool rounds.

Typed assistant text delivered to the client before a turn completes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# TODO(#3402): Replace with channel-agnostic ``UserVisibleChunk`` + ``UserVisibleChunkSink``.
class InTurnInterimOutput(BaseModel):
    """One in-turn sync tool-loop LLM round delivered to the client before turn end."""

    model_config = ConfigDict(extra="forbid")

    text: str
    user_msg_uuid: str
    trace_id: str
    langsmith_trace_id: str
    langsmith_run_id: str
    round_index: int
    had_tool_calls: bool
    assistant_msg_uuid: str
