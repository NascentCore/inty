"""OpenAI chat message shapes shared by turn loop and REPL tools."""

from __future__ import annotations

from typing import Any

# In-memory OpenAI message dicts may carry this key; stripped before API calls.
TRANSCRIPT_MSG_UUID_KEY = "_transcript_uuid"


def openai_assistant_message_dict(msg: Any) -> dict[str, Any]:
    """Convert an OpenAI ChatCompletionMessage to a dict for message history."""
    raw_tool_calls = getattr(msg, "tool_calls", None)
    out: dict[str, Any] = {
        "role": "assistant",
        "content": msg.content if msg.content is not None else "",
    }
    if not raw_tool_calls:
        return out
    tool_calls: list[dict[str, Any]] = []
    for tc in raw_tool_calls:
        fn = tc.function
        tool_calls.append(
            {
                "id": tc.id,
                "type": getattr(tc, "type", "function"),
                "function": {
                    "name": fn.name,
                    "arguments": fn.arguments if fn.arguments is not None else "",
                },
            }
        )
    out["tool_calls"] = tool_calls
    return out
