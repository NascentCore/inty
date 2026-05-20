"""Companion LLM tool catalog: uniqueness and build_* name-set regression."""

from __future__ import annotations

from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
    TOOL_TAG_GENERATION,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
    build_openai_tools,
    tool_has_tag,
)


def _function_tool_names(tools: list) -> list[str]:
    return sorted(
        t["function"]["name"]
        for t in tools
        if t.get("type") == "function" and isinstance(t.get("function"), dict)
    )


def test_build_openai_tools_name_set():
    assert _function_tool_names(build_openai_tools()) == [
        "memory_store_list_paths",
        "memory_store_mkdir",
        "memory_store_read_document",
        "memory_store_write_document",
        "phone_call_user",
        "schedule_task",
        "techno_core_record_event",
        "tool_update_agent_status_line",
        "user_profile_record",
    ]


def test_build_openai_repl_tools_name_set_non_bootstrap():
    assert _function_tool_names(
        build_openai_repl_tools(interactive_bootstrap_active=False)
    ) == [
        "companion_runtime_inspect",
        "companion_set_experience_profile",
        "generate_image",
        "generate_voice_message",
        "google_web_search",
        "living_sphere_record_update",
        "memory_store_list_paths",
        "memory_store_read_document",
        "memory_store_write_document",
        "modify_image",
        "phone_call_user",
        "read_web_page",
        "schedule_task",
        "techno_core_record_event",
        "tool_update_agent_status_line",
        "user_profile_record",
    ]


def test_build_openai_repl_tools_name_set_bootstrap():
    assert _function_tool_names(
        build_openai_repl_tools(interactive_bootstrap_active=True)
    ) == [
        "companion_bootstrap_user_interactive_complete",
        "companion_runtime_inspect",
        "companion_set_experience_profile",
        "companion_update_prompt_slice",
        "generate_image",
        "generate_voice_message",
        "google_web_search",
        "memory_store_list_paths",
        "memory_store_read_document",
        "modify_image",
        "read_web_page",
        "schedule_task",
        "techno_core_record_event",
        "tool_update_agent_status_line",
        "user_profile_record",
    ]


def test_build_openai_repl_tools_inner_tick_name_set():
    assert _function_tool_names(build_openai_repl_tools_inner_tick()) == [
        "memory_store_list_paths",
        "memory_store_read_document",
        "memory_store_write_document",
        "techno_core_record_event",
        "tool_update_agent_status_line",
        "user_profile_record",
    ]


def test_tool_has_tag_generation():
    assert tool_has_tag(CompanionToolName.GENERATE_IMAGE.value, TOOL_TAG_GENERATION)
    assert tool_has_tag(
        CompanionToolName.GENERATE_VOICE_MESSAGE.value, TOOL_TAG_GENERATION
    )
    assert tool_has_tag(CompanionToolName.MODIFY_IMAGE.value, TOOL_TAG_GENERATION)
    assert not tool_has_tag(CompanionToolName.SCHEDULE_TASK.value, TOOL_TAG_GENERATION)
