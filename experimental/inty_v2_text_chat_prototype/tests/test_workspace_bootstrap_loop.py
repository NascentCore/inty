"""run_workspace_bootstrap_loop：工具循环与初始化门控回归。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.workspace_init_loop import run_workspace_bootstrap_loop


def _resp_text(content: str) -> SimpleNamespace:
    msg = SimpleNamespace(content=content, tool_calls=[])
    ch = SimpleNamespace(message=msg, finish_reason="stop")
    return SimpleNamespace(choices=[ch], usage=None)


def _resp_tool(content: str, *, tool_name: str, tool_args: str) -> SimpleNamespace:
    fn = SimpleNamespace(name=tool_name, arguments=tool_args)
    tc = SimpleNamespace(id="call_boot_1", type="function", function=fn)
    msg = SimpleNamespace(content=content, tool_calls=[tc])
    ch = SimpleNamespace(message=msg, finish_reason="tool_calls")
    return SimpleNamespace(choices=[ch], usage=None)


class _FakeBootstrapCompletions:
    """round1 触发工具，round2 返回文本收尾。"""

    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls += 1
        if self.calls == 1:
            return _resp_tool(
                "need init",
                tool_name="workspace_write_file",
                tool_args='{"relative_path":"IDENTITY.md","content":"# I\\n"}',
            )
        if self.calls == 2:
            return _resp_text("ready to know you")
        raise AssertionError(f"unexpected call count: {self.calls}")


class _FakeBootstrapNoTools:
    """始终无工具调用，用于验证 max_rounds 门控。"""

    def create(self, **kwargs: object) -> SimpleNamespace:
        return _resp_text("just chatting")


class TestWorkspaceBootstrapLoop(unittest.TestCase):
    def test_bootstrap_completes_after_tools_initialize_workspace(self) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeBootstrapCompletions())
        )
        tool_calls: list[tuple[str, str]] = []

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def fake_run_tool(name: str, arguments_json: str) -> str:
                tool_calls.append((name, arguments_json))
                files = {
                    "IDENTITY.md": "# I\n",
                    "SOUL.md": "# S\n",
                    "USER.md": "# U\n",
                    "MEMORY.md": "# M\n",
                    "transcript.jsonl": "",
                }
                for rel, body in files.items():
                    (root / rel).write_text(body, encoding="utf-8")
                return "OK initialized"

            with (
                patch(
                    "inty_v2_text_chat_prototype.workspace_init_loop.get_client_dual_llm_tool",
                    return_value=fake_client,
                ),
                patch(
                    "inty_v2_text_chat_prototype.workspace_init_loop.default_model",
                    return_value="fake-model",
                ),
                patch(
                    "inty_v2_text_chat_prototype.workspace_init_loop.tool_executor_for_root",
                    return_value=fake_run_tool,
                ),
                patch(
                    "inty_v2_text_chat_prototype.workspace_init_loop.build_openai_tools",
                    return_value=[{"type": "function"}],
                ),
            ):
                out = run_workspace_bootstrap_loop(
                    root,
                    "hello",
                    companion_type="朋友",
                    max_rounds=4,
                    on_tool=lambda n, a: tool_calls.append((n, a)),
                    llm_trace=False,
                )

        self.assertEqual(out, "ready to know you")
        self.assertGreaterEqual(len(tool_calls), 1)

    def test_bootstrap_raises_when_no_tools_and_workspace_never_initialized(
        self,
    ) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeBootstrapNoTools())
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with (
                patch(
                    "inty_v2_text_chat_prototype.workspace_init_loop.get_client_dual_llm_tool",
                    return_value=fake_client,
                ),
                patch(
                    "inty_v2_text_chat_prototype.workspace_init_loop.default_model",
                    return_value="fake-model",
                ),
                patch(
                    "inty_v2_text_chat_prototype.workspace_init_loop.build_openai_tools",
                    return_value=[{"type": "function"}],
                ),
            ):
                with self.assertRaises(RuntimeError):
                    run_workspace_bootstrap_loop(
                        root,
                        "hello",
                        max_rounds=2,
                        llm_trace=False,
                    )

    def test_bootstrap_raises_on_unknown_companion_type(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError):
                run_workspace_bootstrap_loop(
                    root,
                    "hello",
                    companion_type="同事",
                    max_rounds=1,
                    llm_trace=False,
                )


if __name__ == "__main__":
    unittest.main()
