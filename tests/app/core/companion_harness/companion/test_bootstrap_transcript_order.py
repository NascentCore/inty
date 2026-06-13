"""Bootstrap track must persist transcript.jsonl as user row(s) then assistant row(s)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.proactive_chat import (
    ProactiveChatConfig,
    next_proactive_chat_wait_seconds,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import run_companion_user_chat_turn
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model

_NEVER = 86400.0 * 365.0


def _tool_response(
    *,
    content: str,
    tool_name: str,
    tool_arguments: str,
) -> SimpleNamespace:
    function = SimpleNamespace(name=tool_name, arguments=tool_arguments)
    tool_call = SimpleNamespace(id="tc-1", type="function", function=function)
    message = SimpleNamespace(content=content, tool_calls=[tool_call])
    choice = SimpleNamespace(message=message, finish_reason="tool_calls")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


def _final_response(*, content: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


class _FakeBootstrapLLMClient:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self._responses = iter(responses)

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        return next(self._responses)


def _seed_bootstrap_workspace(store: MemoryStore) -> None:
    store.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "unspecific",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    for rel in ("IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"):
        store.write_document(rel, f"{rel}\n")
    store.write_document("transcript.jsonl", "")


def _bootstrap_deps(
    store: MemoryStore,
    client: _FakeBootstrapLLMClient,
    *,
    bootstrap_interim_output_sink: Any = None,
) -> CompanionTurnDeps:
    tool_bg_idle = threading.Event()
    tool_bg_idle.set()
    return CompanionTurnDeps(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=False,
        memory_bootstrap_type=CompanionMemoryBootstrapType.USER_INTERACTIVE.value,
        runtime_context=TurnRuntimeContext(
            channel=CompanionRuntimeChannel.APP,
            implicit_signal_bundle=None,
        ),
        background_output_sink=None,
        preset_user_msg_uuid=None,
        langsmith_parent_run_enabled=False,
        tool_bg_idle_event=tool_bg_idle,
        bootstrap_interim_output_sink=bootstrap_interim_output_sink,
    )


def _transcript_rows(store: MemoryStore) -> list[dict[str, Any]]:
    body = store.read_document("transcript.jsonl")
    assert body is not None
    return [json.loads(line) for line in body.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_bootstrap_single_round_transcript_user_before_assistant(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("bootstrap-tr-order", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    client = _FakeBootstrapLLMClient(
        [_final_response(content="还没有名字呢")]
    )

    out = await run_companion_user_chat_turn(
        "你叫啥？",
        deps=_bootstrap_deps(store, client),
    )

    rows = _transcript_rows(store)
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["content"] == "你叫啥？"
    assert rows[0]["uuid"] == out.user_msg_uuid
    assert rows[1]["reply_to"] == out.user_msg_uuid
    assert rows[1]["content"] == "还没有名字呢"


@pytest.mark.asyncio
async def test_bootstrap_multi_round_transcript_user_before_all_assistants(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("bootstrap-tr-multi", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    interim: list[BootstrapInterimOutput] = []

    async def _sink(ev: BootstrapInterimOutput) -> None:
        interim.append(ev)

    client = _FakeBootstrapLLMClient(
        [
            _tool_response(
                content="我先记一下",
                tool_name="memory_store_write_document",
                tool_arguments=json.dumps(
                    {
                        "relative_path": "IDENTITY.md",
                        "content": "孔明\n",
                    },
                    ensure_ascii=False,
                ),
            ),
            _final_response(content="从现在起我就是孔明"),
        ]
    )

    out = await run_companion_user_chat_turn(
        "你就叫孔明吧",
        deps=_bootstrap_deps(store, client, bootstrap_interim_output_sink=_sink),
    )

    rows = _transcript_rows(store)
    assert [row["role"] for row in rows] == ["user", "assistant", "assistant"]
    assert rows[0]["uuid"] == out.user_msg_uuid
    assert rows[1]["reply_to"] == out.user_msg_uuid
    assert rows[2]["reply_to"] == out.user_msg_uuid
    assert rows[1]["content"] == "我先记一下"
    assert rows[2]["content"] == "从现在起我就是孔明"
    assert len(interim) == 1
    assert interim[0].text == "我先记一下"


@pytest.mark.asyncio
async def test_bootstrap_transcript_tail_assistant_enables_proactive_scheduling(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("bootstrap-tr-proactive", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    client = _FakeBootstrapLLMClient([_final_response(content="reply")])

    await run_companion_user_chat_turn(
        "hello",
        deps=_bootstrap_deps(store, client),
    )

    cfg = ProactiveChatConfig(min_transcript_lines=2)
    assert next_proactive_chat_wait_seconds(store, cfg) != _NEVER
