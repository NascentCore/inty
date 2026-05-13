"""tools.build_openai_repl_tools respects INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL."""

from __future__ import annotations

from app.core.companion_harness.companion.companion_tool_runtime import (
    build_openai_repl_tools,
)


def _tool_names(tools: list) -> list[str]:
    out = []
    for t in tools:
        if t.get("type") == "function" and "function" in t:
            out.append(t["function"]["name"])
    return out


def test_status_line_tool_present_by_default():
    tools = build_openai_repl_tools(interactive_bootstrap_active=False)
    names = _tool_names(tools)
    assert "tool_update_agent_status_line" in names


def test_status_line_tool_omitted_when_env_set(monkeypatch):
    monkeypatch.setenv("INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL", "1")
    tools = build_openai_repl_tools(interactive_bootstrap_active=False)
    names = _tool_names(tools)
    assert "tool_update_agent_status_line" not in names


def test_status_line_restored_when_env_cleared(monkeypatch):
    monkeypatch.delenv("INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL", raising=False)
    tools = build_openai_repl_tools(interactive_bootstrap_active=False)
    names = _tool_names(tools)
    assert "tool_update_agent_status_line" in names
