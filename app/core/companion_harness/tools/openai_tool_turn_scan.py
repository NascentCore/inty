"""Scan OpenAI-shaped assistant/tool message rows during a tool loop turn."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


def tool_call_names_by_id_from_assistant_message(
    message: dict[str, Any],
) -> dict[str, str]:
    """Map tool_call id → function name from one assistant message with tool_calls."""
    pending: dict[str, str] = {}
    for tool_call in message.get("tool_calls") or []:
        if not isinstance(tool_call, dict):
            continue
        tool_call_id = tool_call.get("id")
        function = tool_call.get("function")
        if not isinstance(function, dict):
            continue
        raw_name = function.get("name")
        if isinstance(tool_call_id, str) and isinstance(raw_name, str):
            name = raw_name.strip()
            if name:
                pending[tool_call_id] = name
    return pending


def iter_tool_results_with_resolved_names(
    messages: list[dict[str, Any]],
) -> Iterator[tuple[str, str, str]]:
    """Yield ``(tool_name, tool_call_id, content)`` for each tool row with a resolved name."""
    pending: dict[str, str] = {}
    for message in messages:
        role = message.get("role")
        if role == "assistant":
            pending = tool_call_names_by_id_from_assistant_message(message)
            continue
        if role != "tool":
            continue
        tool_call_id = message.get("tool_call_id")
        if not isinstance(tool_call_id, str):
            continue
        name = pending.get(tool_call_id)
        if not name:
            continue
        content = str(message.get("content") or "")
        yield name, tool_call_id, content
