"""INNER_TICK_AUTONOMY tool set contract tests."""

from __future__ import annotations

from app.core.companion_harness.memory.memory_store_path_constants import (
    LIFE_CURRENTS_MD_REL,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    COMPANION_LLM_TOOLS_BY_NAME,
    INNER_TICK_AUTONOMY_TOOL_NAMES,
    INNER_TICK_TOOL_NAMES,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    REPL_DESCRIPTION_OVERRIDES_AUTONOMY,
    CompanionToolName,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_repl_tools_inner_tick_autonomy,
)


def test_inner_tick_autonomy_excludes_user_visible_side_effect_tools() -> None:
    names = {tool.value for tool in INNER_TICK_AUTONOMY_TOOL_NAMES}
    assert CompanionToolName.SCHEDULE_TASK.value not in names
    assert CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE.value not in names


def test_inner_tick_autonomy_includes_open_work_tools() -> None:
    names = {tool.value for tool in INNER_TICK_AUTONOMY_TOOL_NAMES}
    assert CompanionToolName.GOOGLE_WEB_SEARCH.value in names
    assert CompanionToolName.GENERATE_IMAGE.value in names
    assert CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT.value in names


def test_inner_tick_monolog_tools_are_ai_private_append_only() -> None:
    monolog_names = {tool.value for tool in INNER_TICK_TOOL_NAMES}
    assert monolog_names == {CompanionToolName.AI_PRIVATE_APPEND.value}


def test_inner_tick_autonomy_and_monolog_tool_sets_are_disjoint() -> None:
    monolog_names = {tool.value for tool in INNER_TICK_TOOL_NAMES}
    autonomy_names = {tool.value for tool in INNER_TICK_AUTONOMY_TOOL_NAMES}
    assert monolog_names.isdisjoint(autonomy_names)


def test_inner_tick_autonomy_tools_are_registered_openai_schemas() -> None:
    for tool in INNER_TICK_AUTONOMY_TOOL_NAMES:
        assert tool.value in COMPANION_LLM_TOOLS_BY_NAME


def test_life_currents_on_memory_store_write_allowlist() -> None:
    assert LIFE_CURRENTS_MD_REL in MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST


def test_autonomy_write_allowlist_is_life_currents_only() -> None:
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY == frozenset(
        {LIFE_CURRENTS_MD_REL}
    )


def test_autonomy_tool_schema_write_description_names_life_currents_only() -> (
    None
):
    write_desc = REPL_DESCRIPTION_OVERRIDES_AUTONOMY[
        CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT
    ]
    assert (
        f"Only writable path via this tool: {LIFE_CURRENTS_MD_REL}" in write_desc
    )
    tools = build_openai_repl_tools_inner_tick_autonomy()
    write_tool = next(
        t
        for t in tools
        if t["function"]["name"] == "memory_store_write_document"
    )
    assert (
        f"Only writable path via this tool: {LIFE_CURRENTS_MD_REL}"
        in write_tool["function"]["description"]
    )
