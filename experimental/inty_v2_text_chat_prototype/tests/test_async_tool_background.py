"""Async tool background mode: chat returns first, tool result is queued later."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
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
    _append_local_image_paths_for_display,
    _background_turn_should_force_tools,
    _last_user_message_text,
    _local_paths_from_tool_messages,
    clear_output_queue,
    pop_output_events_nowait,
)


def _resp_text(content: str) -> SimpleNamespace:
    msg = SimpleNamespace(content=content, tool_calls=[])
    ch = SimpleNamespace(message=msg, finish_reason="stop")
    return SimpleNamespace(choices=[ch], usage=None)


def _resp_tool(content: str, *, tool_name: str, tool_args: str) -> SimpleNamespace:
    fn = SimpleNamespace(name=tool_name, arguments=tool_args)
    tc = SimpleNamespace(id="call_async_1", type="function", function=fn)
    msg = SimpleNamespace(content=content, tool_calls=[tc])
    ch = SimpleNamespace(message=msg, finish_reason="tool_calls")
    return SimpleNamespace(choices=[ch], usage=None)


class _FakeCompletionsAsyncBg:
    def __init__(self) -> None:
        self._tool_calls = 0

    def create(self, **kwargs: object) -> SimpleNamespace:
        model = str(kwargs["model"])
        tools = kwargs.get("tools")
        if model == "chat-fast":
            time.sleep(0.01)
            return _resp_text("chat-fast-r1")
        if model == "tool-smart":
            time.sleep(0.12)
            if tools and self._tool_calls == 0:
                self._tool_calls += 1
                return _resp_tool(
                    "tool-asks-user-profile",
                    tool_name="user_profile_record",
                    tool_args='{"items":[{"label":"昵称","value":"阿木"}]}',
                )
            return _resp_text("tool-final-r2")
        raise AssertionError(f"unexpected model: {model}")


class _FakeCompletionsNoToolCalls:
    def create(self, **kwargs: object) -> SimpleNamespace:
        model = str(kwargs["model"])
        if model == "chat-fast":
            return _resp_text("chat-fast-r1")
        if model == "tool-smart":
            return _resp_text("tool-no-calls-r1")
        raise AssertionError(f"unexpected model: {model}")


class _FakeCompletionsChatSettingsTool:
    def __init__(self) -> None:
        self._chat_calls = 0
        self._tool_calls = 0

    def create(self, **kwargs: object) -> SimpleNamespace:
        model = str(kwargs["model"])
        if model == "chat-fast":
            self._chat_calls += 1
            if self._chat_calls == 1:
                return _resp_tool(
                    "",
                    tool_name="tool_update_chat_settings",
                    tool_args='{"settings_text":"不用括号，短句，少分段。"}',
                )
            if self._chat_calls == 2:
                return _resp_text("收到，后续不用括号。")
        if model == "tool-smart":
            self._tool_calls += 1
            if self._tool_calls == 1:
                return _resp_text("tool-no-calls-r1")
        raise AssertionError(f"unexpected model/call: {model}")


class TestAsyncToolBackground(unittest.TestCase):
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

    def test_chat_returns_first_then_background_event_and_transcript_append(
        self,
    ) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeCompletionsAsyncBg()),
        )
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
                patch.object(
                    orchestrator, "schedule_memory_update_after_turn", return_value=None
                ),
                patch(
                    "inty_v2_text_chat_prototype.tool_background.execute_tool_call",
                    side_effect=lambda *a, **k: "OK tool result",
                ),
                patch.dict(
                    os.environ, {"INTY_V2_PROTO_ASYNC_TOOL_BG": "1"}, clear=False
                ),
            ):
                out = asyncio.run(
                    orchestrator.run_turn(
                        root,
                        "你好",
                        heartbeat_turn=False,
                        llm_trace=False,
                    )
                )
                self.assertEqual(out, "chat-fast-r1")
                # Tool branch is still running or just finished, so immediate queue read can be empty.
                early_events = pop_output_events_nowait(workspace=root)
                self.assertEqual(early_events, [])

                # Wait up to 2s for background result.
                got_events = []
                deadline = time.time() + 2.0
                while time.time() < deadline:
                    got_events = pop_output_events_nowait(workspace=root)
                    if got_events:
                        break
                    asyncio.run(asyncio.sleep(0.01))
                    time.sleep(0.02)
                self.assertEqual(len(got_events), 1)
                self.assertIn("tool-final-r2", got_events[0].text)

            rows = load_transcript((root / "transcript.jsonl"))
            self.assertEqual([r.role for r in rows], ["user", "assistant", "assistant"])
            self.assertEqual(rows[1].content, "chat-fast-r1")
            self.assertEqual(rows[1].source, "chat")
            self.assertEqual(rows[1].reply_to, rows[0].uuid)
            self.assertTrue(rows[0].trace_id)
            self.assertEqual(rows[1].trace_id, rows[0].trace_id)
            self.assertIn("tool-final-r2", rows[2].content)
            self.assertEqual(rows[2].source, "tool_bg")
            self.assertEqual(rows[2].reply_to, rows[0].uuid)
            self.assertEqual(rows[2].trace_id, rows[0].trace_id)

    def test_no_tool_calls_does_not_append_background_transcript(self) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeCompletionsNoToolCalls()),
        )
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
                patch.object(
                    orchestrator, "schedule_memory_update_after_turn", return_value=None
                ),
                patch.dict(
                    os.environ, {"INTY_V2_PROTO_ASYNC_TOOL_BG": "1"}, clear=False
                ),
            ):
                out = asyncio.run(
                    orchestrator.run_turn(
                        root,
                        "你好",
                        heartbeat_turn=False,
                        llm_trace=False,
                    )
                )
                self.assertEqual(out, "chat-fast-r1")
                time.sleep(0.1)
                events = pop_output_events_nowait(workspace=root)
                self.assertEqual(events, [])

            rows = load_transcript((root / "transcript.jsonl"))
            self.assertEqual([r.role for r in rows], ["user", "assistant"])
            self.assertEqual(rows[1].source, "chat")
            self.assertEqual(rows[1].reply_to, rows[0].uuid)
            self.assertTrue(rows[0].trace_id)
            self.assertEqual(rows[1].trace_id, rows[0].trace_id)

    def test_chat_front_tool_update_chat_settings_updates_tools_md(self) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeCompletionsChatSettingsTool()),
        )
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
                patch.object(
                    orchestrator, "schedule_memory_update_after_turn", return_value=None
                ),
                patch.dict(
                    os.environ, {"INTY_V2_PROTO_ASYNC_TOOL_BG": "1"}, clear=False
                ),
            ):
                out = asyncio.run(
                    orchestrator.run_turn(
                        root,
                        "以后不要括号",
                        heartbeat_turn=False,
                        llm_trace=False,
                    )
                )
                self.assertEqual(out, "收到，后续不用括号。")
            tools_md = (root / "TOOLS.md").read_text(encoding="utf-8")
            self.assertIn("## CHAT_SETTINGS（聊天格式元语义）", tools_md)
            self.assertIn("不用括号，短句，少分段。", tools_md)


class TestForceToolsHint(unittest.TestCase):
    def test_last_user_message_text(self) -> None:
        msgs = [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "a"},
            {"role": "user", "content": "生成图片"},
        ]
        self.assertEqual(_last_user_message_text(msgs), "生成图片")

    def test_background_turn_should_force_tools(self) -> None:
        self.assertTrue(_background_turn_should_force_tools("生成图片"))
        self.assertTrue(_background_turn_should_force_tools(" 改图 "))
        self.assertFalse(_background_turn_should_force_tools("你好"))


class TestLocalPathDisplay(unittest.TestCase):
    def test_local_paths_from_tool_messages_dedupes(self) -> None:
        msgs = [
            {"role": "tool", "content": "x local_path=/a/b.jpeg z"},
            {"role": "tool", "content": "local_path=/c/d.jpeg"},
            {"role": "assistant", "content": "nope"},
        ]
        self.assertEqual(
            _local_paths_from_tool_messages(msgs),
            ["/a/b.jpeg", "/c/d.jpeg"],
        )

    def test_append_local_image_paths_for_display(self) -> None:
        t = _append_local_image_paths_for_display("模型正文", ["/tmp/z_image_1.jpeg"])
        self.assertIn("模型正文", t)
        self.assertIn("（生成图片本地路径）", t)
        self.assertIn("/tmp/z_image_1.jpeg", t)


if __name__ == "__main__":
    unittest.main()
