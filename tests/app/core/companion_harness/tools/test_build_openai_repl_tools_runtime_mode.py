"""build_openai_repl_tools respects INTY_RUNTIME_MODE for companion_runtime_inspect."""

from __future__ import annotations

import pytest

from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_repl_tools,
)


def _tool_names(tools: list) -> list[str]:
    out = []
    for t in tools:
        if t.get("type") == "function" and "function" in t:
            out.append(t["function"]["name"])
    return out


def test_runtime_inspect_present_in_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTY_RUNTIME_MODE", "DEBUG")
    names = _tool_names(build_openai_repl_tools(interactive_bootstrap_active=False))
    assert "companion_runtime_inspect" in names


def test_runtime_inspect_absent_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTY_RUNTIME_MODE", "PROD")
    names = _tool_names(build_openai_repl_tools(interactive_bootstrap_active=False))
    assert "companion_runtime_inspect" not in names
