"""Shim: implementation lives in app.core.agentic_kernel.companion.tool_background."""

from __future__ import annotations

from app.core.agentic_kernel.companion.repl_workspace_tools import execute_tool_call
from app.core.agentic_kernel.companion.tool_background import (
    BackgroundToolLoopAborted,
    ToolBackgroundTraceHooks,
    ToolOutputEvent,
    _append_background_log,
    _run_background_tool_loop,
    _append_local_image_paths_for_display,
    _background_turn_should_force_tools,
    _last_user_message_text,
    _local_paths_from_tool_messages,
    background_tasks_count,
    clear_output_queue,
    clear_tool_background_abort_flag,
    is_tool_background_aborted,
    mark_tool_background_aborted,
    output_queue,
    pop_output_events_nowait,
    push_output_event,
    start_tool_background_job,
)

__all__ = [
    "BackgroundToolLoopAborted",
    "ToolBackgroundTraceHooks",
    "ToolOutputEvent",
    "_append_background_log",
    "_run_background_tool_loop",
    "_append_local_image_paths_for_display",
    "_background_turn_should_force_tools",
    "_last_user_message_text",
    "_local_paths_from_tool_messages",
    "background_tasks_count",
    "clear_output_queue",
    "clear_tool_background_abort_flag",
    "execute_tool_call",
    "is_tool_background_aborted",
    "mark_tool_background_aborted",
    "output_queue",
    "pop_output_events_nowait",
    "push_output_event",
    "start_tool_background_job",
]
