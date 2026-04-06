"""tool_path_chat_completion_kwargs: high reasoning on tool-call API paths only."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
if str(_EXPERIMENTAL) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.client import tool_path_chat_completion_kwargs


def _env_without_tool_thinking_flag() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != "INTY_V2_PROTO_TOOL_THINKING"}


class TestToolPathThinkingKwargs(unittest.TestCase):
    def test_deepseek_openrouter_high_reasoning_exclude(self) -> None:
        with patch.dict(os.environ, _env_without_tool_thinking_flag(), clear=True):
            kw = tool_path_chat_completion_kwargs("deepseek/deepseek-v3.2")
            self.assertEqual(
                kw,
                {"extra_body": {"reasoning": {"effort": "high", "exclude": True}}},
            )

    def test_gemini_reasoning_effort_high(self) -> None:
        with patch.dict(os.environ, _env_without_tool_thinking_flag(), clear=True):
            kw = tool_path_chat_completion_kwargs("google/gemini-2.5-flash")
            self.assertEqual(kw, {"reasoning_effort": "high"})

    def test_unknown_model_no_extra_kwargs(self) -> None:
        with patch.dict(os.environ, _env_without_tool_thinking_flag(), clear=True):
            kw = tool_path_chat_completion_kwargs("meta-llama/llama-3.3-70b-instruct")
            self.assertEqual(kw, {})

    def test_disabled_via_env(self) -> None:
        env = _env_without_tool_thinking_flag()
        env["INTY_V2_PROTO_TOOL_THINKING"] = "off"
        with patch.dict(os.environ, env, clear=True):
            kw = tool_path_chat_completion_kwargs("deepseek/deepseek-v3.2")
            self.assertEqual(kw, {})


if __name__ == "__main__":
    unittest.main()
