"""Tests for resolve_official_assistant_tool_loop_async on_assistant_message hook."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.core.companion_harness.tools.runtime import (
    resolve_official_assistant_tool_loop_async,
)


@dataclass
class _Fn:
    name: str
    arguments: str


@dataclass
class _ToolCall:
    id: str
    type: str
    function: _Fn


@dataclass
class _Message:
    content: str | None
    tool_calls: list[_ToolCall] | None = None


@dataclass
class _Choice:
    message: _Message


@dataclass
class _Response:
    choices: list[_Choice]


def _resp(content: str, tool_calls: list[_ToolCall] | None) -> _Response:
    return _Response(choices=[_Choice(message=_Message(content=content, tool_calls=tool_calls))])


@pytest.mark.asyncio
async def test_on_assistant_message_called_each_non_tool_and_tool_round() -> None:
    seen: list[tuple[str, bool]] = []

    async def on_assistant_message(message: Any) -> None:
        body = (message.content or "").strip()
        had_tools = bool(getattr(message, "tool_calls", None) or [])
        seen.append((body, had_tools))

    async def execute_tool_call(
        name: str, raw_arguments: str
    ) -> tuple[str, str | None]:
        assert name == "memory_store_write_document"
        return "OK", None

    round_two = _resp("closing line", None)
    round_one = _resp(
        "hello before tools",
        [_ToolCall(id="tc1", type="function", function=_Fn(name="memory_store_write_document", arguments="{}"))],
    )

    async def continue_chat(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[Any, str | None]:
        return round_two, "trace-2"

    result = await resolve_official_assistant_tool_loop_async(
        response=round_one,
        openai_messages=[{"role": "user", "content": "hi"}],
        max_tool_call_rounds=4,
        execute_tool_call=execute_tool_call,
        continue_chat=continue_chat,
        build_assistant_tool_call_message=lambda m: {
            "role": "assistant",
            "content": m.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in (m.tool_calls or [])
            ],
        },
        insert_system_message=lambda msgs, text: msgs.insert(0, {"role": "system", "content": text}),
        on_assistant_message=on_assistant_message,
    )

    assert seen == [
        ("hello before tools", True),
        ("closing line", False),
    ]
    assert result.response.choices[0].message.content == "closing line"
