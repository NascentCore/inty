"""Agentic tool-call loop for companion run_turn (fake LLM, no network)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.agentic_kernel.companion.llm_client import CompanionLLMClient, CompanionLLMConfig
from app.core.agentic_kernel.companion.memory_pipeline import MemoryPipelineConfig
from app.core.agentic_kernel.companion.memory_store import MemoryStore
from app.core.agentic_kernel.companion.turn import run_turn
from app.core.agentic_kernel.companion.workspace import WorkspacePaths


def _assistant_message(
    *,
    content: str = "",
    tool_calls: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls if tool_calls is not None else [],
    )


def _tool_call(tc_id: str, name: str, arguments: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=tc_id,
        type="function",
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


class _FakeChatCompletions:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = responses
        self._idx = 0

    def create(self, **kwargs: Any) -> SimpleNamespace:
        if self._idx >= len(self._responses):
            raise AssertionError(
                f"unexpected extra chat.completions.create call (idx={self._idx})"
            )
        r = self._responses[self._idx]
        self._idx += 1
        return r


class _FakeLLMClient(CompanionLLMClient):
    def __init__(self, chat_responses: list[SimpleNamespace]) -> None:
        super().__init__(CompanionLLMConfig(api_key="test"))
        self._fake_chat = _FakeChatCompletions(chat_responses)

    def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
    ) -> Any:
        return self._fake_chat.create(
            model=model, messages=messages, tools=tools, tool_choice=tool_choice
        )

    def complete_text(
        self,
        messages: list[dict[str, Any]],
        *,
        model_role: str = "memory",
    ) -> str:
        return ""


@pytest.mark.asyncio
async def test_run_turn_list_dir_then_reply(tmp_path) -> None:
    """
    Use case: model lists workspace root, then answers in natural language.

    Verifies run_turn executes execute_tool_call and feeds tool output back
    before the final assistant message.
    """
    root = tmp_path
    store = MemoryStore(workspace_root=root, repository=None, mirror_to_files=True)
    paths = WorkspacePaths(root=root)
    store.write_document(
        paths.identity.relative_to(root).as_posix(),
        "# ID\nidentity doc",
    )
    store.write_document(
        paths.soul.relative_to(root).as_posix(),
        "# SOUL\nsoul doc",
    )
    store.write_document(
        paths.user_md.relative_to(root).as_posix(),
        "# USER\nInitial profile.",
    )
    store.write_document(
        paths.memory_md.relative_to(root).as_posix(),
        "# MEM\nmemory doc",
    )
    store.write_document(
        paths.transcript.relative_to(root).as_posix(),
        "",
    )
    (root / "context.json").write_text("{}", encoding="utf-8")
    (root / "hello.txt").write_text("hi", encoding="utf-8")

    list_call = _tool_call("call-list", "workspace_list_dir", {"path": "."})
    responses = [
        SimpleNamespace(choices=[SimpleNamespace(message=_assistant_message(tool_calls=[list_call]))]),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=_assistant_message(
                        content="I see hello.txt in the workspace root."
                    )
                )
            ]
        ),
    ]
    client = _FakeLLMClient(responses)

    mem_cfg = MemoryPipelineConfig(
        day_summary_disabled=True,
        user_update_disabled=True,
        soul_update_disabled=True,
    )
    out = await run_turn(
        root,
        "What files are at the workspace root?",
        store=store,
        llm_client=client,
        defer_memory_update=False,
        memory_config=mem_cfg,
    )

    assert out == "I see hello.txt in the workspace root."
    assert client._fake_chat._idx == 2
    tr = store.read_document("transcript.jsonl")
    assert "hello.txt" in tr
    assert "I see hello.txt" in tr
