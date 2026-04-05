"""REPL repl_cancel_check / tool_bg abort for superseded turns."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype import orchestrator
from inty_v2_text_chat_prototype.models import load_transcript
from inty_v2_text_chat_prototype.paths import WorkspacePaths
from inty_v2_text_chat_prototype.tool_background import (
    _run_background_tool_loop,
    clear_output_queue,
    is_tool_background_aborted,
    mark_tool_background_aborted,
)
from inty_v2_text_chat_prototype.workspace_init_tools import execute_tool_call


def _resp_text(content: str) -> SimpleNamespace:
    msg = SimpleNamespace(content=content, tool_calls=[])
    ch = SimpleNamespace(message=msg, finish_reason="stop")
    return SimpleNamespace(choices=[ch], usage=None)


class TestReplSupersede(unittest.TestCase):
    def setUp(self) -> None:
        clear_output_queue()

    def tearDown(self) -> None:
        clear_output_queue()

    def _init_workspace(self, root: Path) -> WorkspacePaths:
        paths = WorkspacePaths(root=root)
        paths.identity.write_text("# I\n", encoding="utf-8")
        paths.soul.write_text("# S\n", encoding="utf-8")
        paths.user_md.write_text("# U\n", encoding="utf-8")
        paths.memory_md.write_text("# M\n", encoding="utf-8")
        paths.transcript.write_text("", encoding="utf-8")
        return paths

    def test_run_turn_repl_cancel_immediate_raises_and_skips_transcript(self) -> None:
        class _C:
            def create(self, **kwargs: object) -> SimpleNamespace:
                return _resp_text("x")

        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_C()))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_workspace(root)
            with (
                patch.object(orchestrator, "get_client", return_value=fake_client),
                patch.object(
                    orchestrator,
                    "get_client_dual_llm_chat",
                    return_value=fake_client,
                ),
                patch.object(
                    orchestrator,
                    "get_client_dual_llm_tool",
                    return_value=fake_client,
                ),
                patch.object(orchestrator, "chat_model", return_value="chat-fast"),
                patch.object(orchestrator, "tool_model", return_value="tool-smart"),
                patch.object(
                    orchestrator,
                    "build_openai_repl_tools",
                    return_value=[{"type": "function"}],
                ),
                patch.dict(
                    os.environ, {"INTY_V2_PROTO_ASYNC_TOOL_BG": "1"}, clear=False
                ),
            ):
                with self.assertRaises(orchestrator.ReplTurnSuperseded):
                    asyncio.run(
                        orchestrator.run_turn(
                            root,
                            "你好",
                            llm_trace=False,
                            repl_cancel_check=lambda: True,
                        )
                    )
            rows = load_transcript(root / "transcript.jsonl")
            self.assertEqual(rows, [])

    def test_tool_background_aborted_at_start_clears_flag(self) -> None:
        uid = "deadbeef-dead-beef-dead-beefdeadbeef"
        mark_tool_background_aborted(uid)
        self.assertTrue(is_tool_background_aborted(uid))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = self._init_workspace(root)

            async def _run() -> None:
                await _run_background_tool_loop(
                    ws_root=root,
                    request_messages=[{"role": "user", "content": "hi"}],
                    tool_model_name="tool-smart",
                    llm_trace=False,
                    transcript_path=paths.transcript,
                    user_msg_uuid=uid,
                    trace_id="trace-1",
                    tools=[{"type": "function"}],
                    on_event=lambda _ev: None,
                    execute_tool_call_fn=execute_tool_call,
                    client=None,
                )

            asyncio.run(_run())
        self.assertFalse(is_tool_background_aborted(uid))
        rows = load_transcript(paths.transcript)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
