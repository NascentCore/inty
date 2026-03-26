from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolRuntimeResult:
    """Standardized result of one tool-call processing step."""

    messages: list[dict[str, Any]]
    assistant_text: str
    tool_result: str
    done: bool
    image_path: str | None


def process_single_tool_call(
    *,
    messages: list[dict[str, Any]],
    message: Any,
    tool_executors: dict[str, Callable[..., tuple[str, str | None]]],
    tool_types: dict[str, Any],
    tool_context_types: dict[str, Any],
    get_tool_context: Callable[[Any, list[dict[str, Any]]], dict[str, Any]],
    is_terminal_tool: Callable[[Any], bool],
    unknown_tool_message: Callable[[str], str] | None = None,
) -> ToolRuntimeResult:
    """
    Process exactly one tool_call from an assistant message.

    This keeps behavior minimal/compatible with existing prototype logic:
    - append assistant tool_call message
    - execute one tool with parsed JSON args + built context
    - append tool result message
    - return done/content based on tool terminality
    """
    raw_tool_calls = getattr(message, "tool_calls", None) or []
    assert len(raw_tool_calls) >= 1, "process_single_tool_call requires at least one tool_call"
    assert len(raw_tool_calls) <= 1, "parallel_tool_calls are not supported"

    tool_call = raw_tool_calls[0]
    assistant_text = (message.content or "").strip()
    name = tool_call.function.name
    raw_args = tool_call.function.arguments or ""

    tc_dict: dict[str, Any] = {
        "id": tool_call.id,
        "type": getattr(tool_call, "type", "function"),
        "function": {
            "name": name,
            "arguments": raw_args,
        },
    }
    assistant_msg = {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [tc_dict],
    }
    new_messages = [*messages, assistant_msg]

    try:
        parsed_args = json.loads(raw_args) if raw_args.strip() else {}
    except json.JSONDecodeError:
        parsed_args = {}

    context_type = tool_context_types.get(name)
    context_kwargs = get_tool_context(context_type, new_messages)

    executor = tool_executors.get(name)
    if executor is None:
        if unknown_tool_message is None:
            result = f"unknown tool: {name}"
        else:
            result = unknown_tool_message(name)
        image_path = None
    else:
        result, image_path = executor(**parsed_args, **context_kwargs)

    new_messages.append(
        {"role": "tool", "tool_call_id": tool_call.id, "content": result}
    )

    terminal = is_terminal_tool(tool_types.get(name))
    return ToolRuntimeResult(
        messages=new_messages,
        assistant_text=assistant_text,
        tool_result=result,
        done=terminal,
        image_path=image_path,
    )
