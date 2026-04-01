"""tool_path_chat_completion_kwargs: high reasoning on tool-call API paths only."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.client import tool_path_chat_completion_kwargs


@pytest.fixture
def _clear_tool_thinking_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTY_V2_PROTO_TOOL_THINKING", raising=False)


def test_deepseek_openrouter_high_reasoning_exclude(
    _clear_tool_thinking_env: None,
) -> None:
    kw = tool_path_chat_completion_kwargs("deepseek/deepseek-v3.2")
    assert kw == {
        "extra_body": {"reasoning": {"effort": "high", "exclude": True}},
    }


def test_gemini_reasoning_effort_high(_clear_tool_thinking_env: None) -> None:
    kw = tool_path_chat_completion_kwargs("google/gemini-2.5-flash")
    assert kw == {"reasoning_effort": "high"}


def test_unknown_model_no_extra_kwargs(_clear_tool_thinking_env: None) -> None:
    kw = tool_path_chat_completion_kwargs("meta-llama/llama-3.3-70b-instruct")
    assert kw == {}


def test_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTY_V2_PROTO_TOOL_THINKING", "off")
    kw = tool_path_chat_completion_kwargs("deepseek/deepseek-v3.2")
    assert kw == {}
