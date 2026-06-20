"""openai_tools_prepare: strict injection for Chat Completions tools."""

from __future__ import annotations

import pytest

from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_repl_tools,
)
from app.core.companion_harness.tools.openai_tools_prepare import (
    openai_tools_strict_default_from_env,
    prepare_openai_tools_for_chat_completions,
)


def _function_tools(tools: list) -> list[dict]:
    return [
        t
        for t in tools
        if t.get("type") == "function" and isinstance(t.get("function"), dict)
    ]


def test_prepare_sets_strict_without_mutating_original_function_dict():
    inner: dict = {
        "name": "dummy",
        "description": "x",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    }
    tools = [{"type": "function", "function": inner}]
    out = prepare_openai_tools_for_chat_completions(tools, strict=True)
    assert "strict" not in inner
    assert out[0]["function"]["strict"] is True
    assert tools[0]["function"] is inner


def test_prepare_strict_false_explicit():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "a",
                "description": "d",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            },
        }
    ]
    out = prepare_openai_tools_for_chat_completions(tools, strict=False)
    assert out[0]["function"]["strict"] is False


def test_build_openai_repl_tools_all_functions_strict_true(monkeypatch):
    monkeypatch.delenv("INTY_OPENAI_TOOLS_STRICT", raising=False)
    tools = build_openai_repl_tools()
    for t in _function_tools(tools):
        assert t["function"].get("strict") is True


def test_build_openai_repl_tools_strict_false_when_env_off(monkeypatch):
    monkeypatch.setenv("INTY_OPENAI_TOOLS_STRICT", "0")
    tools = build_openai_repl_tools()
    for t in _function_tools(tools):
        assert t["function"].get("strict") is False


def test_strict_env_invalid_raises(monkeypatch):
    monkeypatch.setenv("INTY_OPENAI_TOOLS_STRICT", "maybe")
    with pytest.raises(ValueError, match="INTY_OPENAI_TOOLS_STRICT"):
        openai_tools_strict_default_from_env()
