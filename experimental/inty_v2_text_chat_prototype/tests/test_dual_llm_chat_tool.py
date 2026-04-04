"""Dual-LLM chat/tool routing: same-context invocation and continuous history merge."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import threading
import time
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype import orchestrator
from inty_v2_text_chat_prototype.models import ContextMeta, PromptBundle


def _resp_text(content: str) -> SimpleNamespace:
    msg = SimpleNamespace(content=content, tool_calls=[])
    ch = SimpleNamespace(message=msg, finish_reason="stop")
    return SimpleNamespace(choices=[ch], usage=None)


def _resp_tool(content: str, *, tool_name: str, tool_args: str) -> SimpleNamespace:
    fn = SimpleNamespace(name=tool_name, arguments=tool_args)
    tc = SimpleNamespace(id="call_1", type="function", function=fn)
    msg = SimpleNamespace(content=content, tool_calls=[tc])
    ch = SimpleNamespace(message=msg, finish_reason="tool_calls")
    return SimpleNamespace(choices=[ch], usage=None)


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self._per_model_count: dict[str, int] = {}
        self._lock = threading.Lock()

    def create(self, **kwargs: object) -> SimpleNamespace:
        model = str(kwargs["model"])
        messages = deepcopy(kwargs["messages"])
        tools = deepcopy(kwargs.get("tools"))
        with self._lock:
            self.calls.append(
                {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                }
            )
            idx = self._per_model_count.get(model, 0) + 1
            self._per_model_count[model] = idx
        if model == "chat-fast":
            time.sleep(0.01)
            if idx == 1:
                return _resp_text("chat-r1")
            if idx == 2:
                return _resp_text("chat-r2")
        if model == "tool-smart":
            time.sleep(0.03)
            if idx == 1:
                return _resp_tool(
                    "tool-r1",
                    tool_name="user_profile_record",
                    tool_args='{"items":[{"label":"昵称","value":"阿木"}]}',
                )
            if idx == 2:
                return _resp_text("tool-r2")
        raise AssertionError(f"unexpected model/round: {model=} {idx=}")


class _FakeCompletionsToolFirst:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self._per_model_count: dict[str, int] = {}
        self._lock = threading.Lock()

    def create(self, **kwargs: object) -> SimpleNamespace:
        model = str(kwargs["model"])
        messages = deepcopy(kwargs["messages"])
        tools = deepcopy(kwargs.get("tools"))
        with self._lock:
            self.calls.append(
                {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                }
            )
            idx = self._per_model_count.get(model, 0) + 1
            self._per_model_count[model] = idx
        if model == "chat-fast":
            time.sleep(0.03)
            if idx == 1:
                return _resp_text("chat-r1")
            if idx == 2:
                return _resp_text("chat-r2")
        if model == "tool-smart":
            time.sleep(0.01)
            if idx == 1:
                return _resp_tool(
                    "tool-r1",
                    tool_name="user_profile_record",
                    tool_args='{"items":[{"label":"昵称","value":"阿木"}]}',
                )
            if idx == 2:
                return _resp_text("tool-r2")
        raise AssertionError(f"unexpected model/round: {model=} {idx=}")


class TestDualLlmChatTool(unittest.TestCase):
    def test_dual_llm_uses_same_context_and_merges_history_continuously(self) -> None:
        fake_completions = _FakeCompletions()
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions),
        )
        fake_execute_tool_call = AsyncMock(return_value="OK tool result")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            messages: list[dict[str, object]] = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "u1"},
            ]
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
                patch.object(orchestrator, "dual_llm_enabled", return_value=True),
                patch.object(orchestrator, "chat_model", return_value="chat-fast"),
                patch.object(orchestrator, "tool_model", return_value="tool-smart"),
                patch.object(
                    orchestrator,
                    "build_openai_repl_tools",
                    return_value=[{"type": "function"}],
                ),
                patch.object(
                    orchestrator,
                    "execute_tool_call",
                    fake_execute_tool_call,
                ),
            ):
                out = asyncio.run(
                    orchestrator._run_turn_with_user_profile_tools(
                        messages,
                        root,
                        llm_trace=False,
                        heartbeat_turn=False,
                    )
                )

        self.assertEqual(out, "chat-r2\n\ntool-r2")
        self.assertEqual(len(fake_completions.calls), 4)
        chat_calls = [c for c in fake_completions.calls if c["model"] == "chat-fast"]
        tool_calls = [c for c in fake_completions.calls if c["model"] == "tool-smart"]
        self.assertEqual(len(chat_calls), 2)
        self.assertEqual(len(tool_calls), 2)

        # Round-wise, both routes must receive exactly the same context snapshot.
        self.assertEqual(chat_calls[0]["messages"], tool_calls[0]["messages"])
        self.assertEqual(chat_calls[1]["messages"], tool_calls[1]["messages"])

        # The second-round context already contains both branch outputs + tool result.
        second_payload = chat_calls[1]["messages"]
        assistant_bodies = [
            str(m.get("content", ""))
            for m in second_payload
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]
        self.assertIn("chat-r1", assistant_bodies)
        self.assertIn("tool-r1", assistant_bodies)
        tool_bodies = [
            str(m.get("content", ""))
            for m in second_payload
            if isinstance(m, dict) and m.get("role") == "tool"
        ]
        self.assertIn("OK tool result", tool_bodies)

        fake_execute_tool_call.assert_awaited_once()

    def test_dual_llm_keeps_tool_call_adjacent_when_tool_branch_finishes_first(
        self,
    ) -> None:
        fake_completions = _FakeCompletionsToolFirst()
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions),
        )
        fake_execute_tool_call = AsyncMock(return_value="OK tool result")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            messages: list[dict[str, object]] = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "u1"},
            ]
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
                patch.object(orchestrator, "dual_llm_enabled", return_value=True),
                patch.object(orchestrator, "chat_model", return_value="chat-fast"),
                patch.object(orchestrator, "tool_model", return_value="tool-smart"),
                patch.object(
                    orchestrator,
                    "build_openai_repl_tools",
                    return_value=[{"type": "function"}],
                ),
                patch.object(
                    orchestrator,
                    "execute_tool_call",
                    fake_execute_tool_call,
                ),
            ):
                out = asyncio.run(
                    orchestrator._run_turn_with_user_profile_tools(
                        messages,
                        root,
                        llm_trace=False,
                        heartbeat_turn=False,
                    )
                )

        self.assertEqual(out, "chat-r2\n\ntool-r2")
        self.assertEqual(len(fake_completions.calls), 4)
        # After round-1 execution, ordering must keep tool protocol contiguous:
        # tool assistant(tool_calls) -> tool result before any round-2 assistant messages.
        tool_idx = next(
            i
            for i, m in enumerate(messages)
            if isinstance(m, dict)
            and m.get("role") == "assistant"
            and m.get("content") == "tool-r1"
        )
        result_idx = next(
            i
            for i, m in enumerate(messages)
            if isinstance(m, dict)
            and m.get("role") == "tool"
            and m.get("content") == "OK tool result"
        )
        chat2_idx = next(
            i
            for i, m in enumerate(messages)
            if isinstance(m, dict)
            and m.get("role") == "assistant"
            and m.get("content") == "chat-r2"
        )
        self.assertEqual(result_idx, tool_idx + 1)
        self.assertLess(result_idx, chat2_idx)
        fake_execute_tool_call.assert_awaited_once()

    def test_tool_update_chat_settings_updates_next_chat_branch_system_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            messages: list[dict[str, object]] = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "u1"},
            ]

            async def _fake_execute_tool_call(
                root_arg: Path,
                name: str,
                arguments_json: str,
                *,
                write_allowlist: frozenset[str] | None = None,
            ) -> str:
                self.assertEqual(name, "tool_update_chat_settings")
                self.assertEqual(write_allowlist, orchestrator.REPL_WRITABLE_RELATIVE_PATHS)
                (root_arg / ".inty_v2_chat_settings.json").write_text(
                    '{"chat_output_format_prompt":"必须输出 JSON: {\\"reply\\":\\"...\\"}"}\n',
                    encoding="utf-8",
                )
                return "OK updated chat output format prompt"

            def _tool_resp_with_update(content: str) -> SimpleNamespace:
                fn = SimpleNamespace(
                    name="tool_update_chat_settings",
                    arguments='{"output_format_prompt":"必须输出 JSON: {\\"reply\\":\\"...\\"}"}',
                )
                tc = SimpleNamespace(id="call_settings_1", type="function", function=fn)
                msg = SimpleNamespace(content=content, tool_calls=[tc])
                ch = SimpleNamespace(message=msg, finish_reason="tool_calls")
                return SimpleNamespace(choices=[ch], usage=None)

            class _FakeCompletionsWithSettings(_FakeCompletions):
                def create(self, **kwargs: object) -> SimpleNamespace:
                    model = str(kwargs["model"])
                    messages_payload = deepcopy(kwargs["messages"])
                    tools = deepcopy(kwargs.get("tools"))
                    with self._lock:
                        self.calls.append(
                            {
                                "model": model,
                                "messages": messages_payload,
                                "tools": tools,
                            }
                        )
                        idx = self._per_model_count.get(model, 0) + 1
                        self._per_model_count[model] = idx
                    if model == "chat-fast":
                        if idx == 1:
                            return _resp_text("chat-r1")
                        if idx == 2:
                            return _resp_text("chat-r2")
                    if model == "tool-smart":
                        if idx == 1:
                            return _tool_resp_with_update("tool-r1")
                        if idx == 2:
                            return _resp_text("tool-r2")
                    raise AssertionError(f"unexpected model/round: {model=} {idx=}")

            fake_completions2 = _FakeCompletionsWithSettings()
            fake_client2 = SimpleNamespace(
                chat=SimpleNamespace(completions=fake_completions2),
            )
            with (
                patch.object(orchestrator, "get_client", return_value=fake_client2),
                patch.object(
                    orchestrator,
                    "get_client_dual_llm_chat",
                    return_value=fake_client2,
                ),
                patch.object(
                    orchestrator,
                    "get_client_dual_llm_tool",
                    return_value=fake_client2,
                ),
                patch.object(orchestrator, "dual_llm_enabled", return_value=True),
                patch.object(orchestrator, "chat_model", return_value="chat-fast"),
                patch.object(orchestrator, "tool_model", return_value="tool-smart"),
                patch.object(
                    orchestrator,
                    "build_openai_repl_tools",
                    return_value=[{"type": "function"}],
                ),
                patch.object(
                    orchestrator,
                    "execute_tool_call",
                    _fake_execute_tool_call,
                ),
            ):
                out = asyncio.run(
                    orchestrator._run_turn_with_user_profile_tools(
                        messages,
                        root,
                        llm_trace=False,
                        heartbeat_turn=False,
                        bundle=PromptBundle(
                            identity="id",
                            soul="soul",
                            user_md="user",
                            memory_md="memory",
                        ),
                        context=ContextMeta(),
                    )
                )

        self.assertEqual(out, "chat-r2\n\ntool-r2")
        chat_calls = [c for c in fake_completions2.calls if c["model"] == "chat-fast"]
        self.assertEqual(len(chat_calls), 2)
        round2_system = str(chat_calls[1]["messages"][0]["content"])
        self.assertIn("CHAT 输出格式约束", round2_system)
        self.assertIn('必须输出 JSON: {"reply":"..."}', round2_system)


if __name__ == "__main__":
    unittest.main()
