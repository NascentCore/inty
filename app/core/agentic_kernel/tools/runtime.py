from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class ToolRuntimeResult:
    """Standardized result of one tool-call processing step."""

    messages: list[dict[str, Any]]
    assistant_text: str
    tool_result: str
    done: bool
    image_path: str | None


@dataclass(frozen=True)
class OfficialAssistantToolLoopResult:
    """Result of resolving official assistant tool-call rounds."""

    response: Any
    messages: list[dict[str, Any]]
    trace_id: str | None


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
    assert (
        len(raw_tool_calls) >= 1
    ), "process_single_tool_call requires at least one tool_call"
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


def resolve_official_assistant_tool_loop(
    *,
    response: Any,
    openai_messages: list[dict[str, Any]],
    max_tool_call_rounds: int,
    execute_tool_call: Callable[[str, str], tuple[str, str | None]],
    continue_chat: Callable[[list[dict[str, Any]]], tuple[Any, str | None]],
    build_assistant_tool_call_message: Callable[[Any], dict[str, Any]],
    insert_system_message: Callable[[list[dict[str, Any]], str], None],
    initial_trace_id: str | None = None,
) -> OfficialAssistantToolLoopResult:
    """
    Resolve OpenAI-style tool-call rounds for official assistant chat flow.

    The behavior is intentionally minimal and parity-oriented:
    - append assistant tool_call message
    - execute each tool call and append tool result message
    - inject system messages returned by tools
    - continue chat until no tool calls or round limit reached
    """
    messages_with_tool_results = [*openai_messages]
    current_response = response
    last_trace_id = initial_trace_id
    for _ in range(max_tool_call_rounds):
        current_message = current_response.choices[0].message
        tool_calls = getattr(current_message, "tool_calls", None) or []
        if not tool_calls:
            return OfficialAssistantToolLoopResult(
                response=current_response,
                messages=messages_with_tool_results,
                trace_id=last_trace_id,
            )

        messages_with_tool_results.append(
            build_assistant_tool_call_message(current_message)
        )
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments or ""
            tool_result, injected_system_message = execute_tool_call(
                tool_name,
                raw_arguments,
            )
            messages_with_tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                }
            )
            if injected_system_message:
                insert_system_message(
                    messages_with_tool_results,
                    injected_system_message,
                )
        current_response, last_trace_id = continue_chat(messages_with_tool_results)

    raise ValueError(
        "Official assistant tool call rounds exceeded " f"limit={max_tool_call_rounds}"
    )


async def resolve_official_assistant_tool_loop_async(
    *,
    response: Any,
    openai_messages: list[dict[str, Any]],
    max_tool_call_rounds: int,
    execute_tool_call: Callable[[str, str], Awaitable[tuple[str, str | None]]],
    continue_chat: Callable[[list[dict[str, Any]]], Awaitable[tuple[Any, str | None]]],
    build_assistant_tool_call_message: Callable[[Any], dict[str, Any]],
    insert_system_message: Callable[[list[dict[str, Any]], str], None],
    initial_trace_id: str | None = None,
    after_tool_messages_appended: (
        Callable[[list[dict[str, Any]]], Awaitable[None]] | None
    ) = None,
) -> OfficialAssistantToolLoopResult:
    """
    Async variant of official assistant tool-call loop.

    Keep semantics aligned with `resolve_official_assistant_tool_loop`, but
    allow async tool execution and async model continuation in the same event loop.

    ``after_tool_messages_appended`` runs once per tool round, after all tool
    results (and any injected system messages) are appended and before
    ``continue_chat``. Callers use it to refresh leading system messages or tool
    definitions when workspace slices change mid-loop (e.g. bootstrap complete).
    """
    messages_with_tool_results = [*openai_messages]
    current_response = response
    last_trace_id = initial_trace_id
    for _ in range(max_tool_call_rounds):
        current_message = current_response.choices[0].message
        tool_calls = getattr(current_message, "tool_calls", None) or []
        if not tool_calls:
            return OfficialAssistantToolLoopResult(
                response=current_response,
                messages=messages_with_tool_results,
                trace_id=last_trace_id,
            )

        messages_with_tool_results.append(
            build_assistant_tool_call_message(current_message)
        )
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments or ""
            tool_result, injected_system_message = await execute_tool_call(
                tool_name,
                raw_arguments,
            )
            messages_with_tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                }
            )
            if injected_system_message:
                insert_system_message(
                    messages_with_tool_results,
                    injected_system_message,
                )
        if after_tool_messages_appended is not None:
            await after_tool_messages_appended(messages_with_tool_results)
        current_response, last_trace_id = await continue_chat(
            messages_with_tool_results
        )

    raise ValueError(
        "Official assistant tool call rounds exceeded " f"limit={max_tool_call_rounds}"
    )
