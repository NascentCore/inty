"""run_workspace_bootstrap_loop：工具循环与 BOOSTRAPED 门控回归。"""

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
    """round1 写 BOOSTRAPED，round2 返回文本收尾。"""

    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls += 1
        if self.calls == 1:
            return _resp_tool(
                "write marker",
                tool_name="workspace_write_file",
                tool_args='{"relative_path":"BOOSTRAPED","content":""}',
            )
        if self.calls == 2:
            return _resp_text("ready to know you")
        raise AssertionError(f"unexpected call count: {self.calls}")


class _FakeBootstrapNoTools:
    """始终无工具调用，用于验证 max_rounds 门控。"""

    def create(self, **kwargs: object) -> SimpleNamespace:
        return _resp_text("just chatting")


def _seed_initialized_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "IDENTITY.md").write_text("# I\n", encoding="utf-8")
    (root / "SOUL.md").write_text("# S\n", encoding="utf-8")
    (root / "USER.md").write_text("# U\n", encoding="utf-8")
    (root / "MEMORY.md").write_text("# M\n", encoding="utf-8")
    (root / "transcript.jsonl").write_text("", encoding="utf-8")


class TestWorkspaceBootstrapLoop(unittest.TestCase):
    def test_bootstrap_completes_after_tool_writes_boostraped_marker(self) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeBootstrapCompletions())
        )
        tool_calls: list[tuple[str, str]] = []

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seed_initialized_workspace(root)

            def fake_run_tool(name: str, arguments_json: str) -> str:
                tool_calls.append((name, arguments_json))
                (root / "BOOSTRAPED").write_text("", encoding="utf-8")
                return "OK"

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
                    max_rounds=4,
                    on_tool=lambda n, a: tool_calls.append((n, a)),
                    llm_trace=False,
                )
            self.assertEqual(out, "ready to know you")
            self.assertGreaterEqual(len(tool_calls), 1)
            self.assertTrue((root / "BOOSTRAPED").is_file())

    def test_bootstrap_raises_when_no_tools_and_marker_missing(self) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeBootstrapNoTools())
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seed_initialized_workspace(root)
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


if __name__ == "__main__":
    unittest.main()
