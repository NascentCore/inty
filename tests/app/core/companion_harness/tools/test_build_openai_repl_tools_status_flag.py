"""REPL tool surface omits tool_update_agent_status_line (not LLM-callable)."""

from __future__ import annotations

from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
)


def _tool_names(tools: list) -> list[str]:
    out = []
    for t in tools:
        if t.get("type") == "function" and "function" in t:
            out.append(t["function"]["name"])
    return out


def test_status_line_tool_omitted_from_repl_tools():
    for bootstrap in (False, True):
        tools = build_openai_repl_tools(interactive_bootstrap_active=bootstrap)
        assert "tool_update_agent_status_line" not in _tool_names(tools)


def test_status_line_tool_omitted_from_inner_tick_repl_tools():
    tools = build_openai_repl_tools_inner_tick()
    assert "tool_update_agent_status_line" not in _tool_names(tools)
