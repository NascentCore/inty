"""Shim: companion tool execution lives in companion.companion_tool_runtime."""

from __future__ import annotations

from app.core.agentic_kernel.companion.fal_z_image_tool import (
    MAX_NUM_IMAGES_PER_CALL,
    reset_fal_async_client_after_short_lived_loop,
    run_generate_image_z_image_turbo,
    run_modify_image_z_image_turbo,
)
from app.core.agentic_kernel.companion.message_format import openai_assistant_message_dict
from app.core.agentic_kernel.companion.companion_tool_runtime import (
    REPL_WRITABLE_RELATIVE_PATHS,
    TEXT_RESPONSE_INCLUDE_IN_CHAT,
    WORKSPACE_READ_FILE_MAX_CHARS_CAP,
    append_user_profile_facts_to_user_md,
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
    build_openai_tools,
    execute_tool_call,
    execute_tool_call_blocking,
    read_chat_output_format_prompt,
    resolve_under_workspace,
    tool_executor_for_root,
    tool_has_tag,
    tool_schedule_task,
    tool_text_response_include_in_chat,
    tool_text_response_should_include_in_chat,
    tool_update_chat_settings,
    tool_user_profile_record,
    tool_workspace_list_dir,
    tool_workspace_mkdir,
    tool_workspace_read_file,
    tool_workspace_write_file,
)

_reset_fal_async_client_after_short_lived_loop = reset_fal_async_client_after_short_lived_loop
