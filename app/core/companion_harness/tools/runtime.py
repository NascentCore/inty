"""Tool-call runtime helpers shared by Companion Harness chat flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class OfficialAssistantToolLoopResult:
    """Result of resolving official assistant tool-call rounds."""

    response: Any
    messages: list[dict[str, Any]]
    trace_id: str | None


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
    on_assistant_message: Callable[[Any], None] | None = None,
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
        if on_assistant_message is not None:
            on_assistant_message(current_message)
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
        current_response, last_trace_id = continue_chat(
            messages_with_tool_results
        )

    raise ValueError(
        "Official assistant tool call rounds exceeded "
        f"limit={max_tool_call_rounds}"
    )


async def resolve_official_assistant_tool_loop_async(
    *,
    response: Any,
    openai_messages: list[dict[str, Any]],
    max_tool_call_rounds: int,
    execute_tool_call: Callable[[str, str], Awaitable[tuple[str, str | None]]],
    continue_chat: Callable[
        [list[dict[str, Any]]], Awaitable[tuple[Any, str | None]]
    ],
    build_assistant_tool_call_message: Callable[[Any], dict[str, Any]],
    insert_system_message: Callable[[list[dict[str, Any]], str], None],
    initial_trace_id: str | None = None,
    after_tool_messages_appended: (
        Callable[[list[dict[str, Any]]], Awaitable[None]] | None
    ) = None,
    on_assistant_message: Callable[[Any], Awaitable[None]] | None = None,
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
        if on_assistant_message is not None:
            await on_assistant_message(current_message)
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
        "Official assistant tool call rounds exceeded "
        f"limit={max_tool_call_rounds}"
    )


def insert_openai_system_message(
    openai_messages: list[dict[str, Any]],
    system_message_content: str,
) -> None:
    """Insert tool-injected system text after the leading system-message prefix."""
    insertion_index = 0
    while (
        insertion_index < len(openai_messages)
        and openai_messages[insertion_index].get("role") == "system"
    ):
        insertion_index += 1
    openai_messages.insert(
        insertion_index, {"role": "system", "content": system_message_content}
    )
