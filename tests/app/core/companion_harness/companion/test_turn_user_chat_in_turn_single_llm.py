"""Settled USER_CHAT uses in-turn sync tool loop (no dual-LLM foreground)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
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


class _FakeInTurnSyncLLMClient:
    def __init__(
        self,
        responses: list[SimpleNamespace] | None = None,
    ) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self.chat_calls: list[dict[str, Any]] = []
        if responses is None:
            responses = [_final_response(content="sync in-turn reply")]
        self._responses = iter(responses)

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        self.chat_calls.append(kwargs)
        return next(self._responses)


def _seed_settled_workspace(store: MemoryStore) -> None:
    store.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "intimate",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    for rel in ("IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"):
        store.write_document(rel, f"{rel}\n")
    store.write_document("transcript.jsonl", "")


def _user_chat_deps(
    store: MemoryStore,
    client: _FakeInTurnSyncLLMClient,
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
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
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
async def test_user_chat_in_turn_single_llm_no_tool_background(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    scope = CompanionScope("sync-llm", "a", str(tmp_path.resolve()))
    store = MemoryStore(scope=scope, repository=None)
    _seed_settled_workspace(store)
    client = _FakeInTurnSyncLLMClient()

    out = await run_companion_user_chat_turn(
        "hello single llm",
        deps=_user_chat_deps(store, client),
    )

    assert out.tool_background_started is False
    assert out.assistant_text == "sync in-turn reply"
    assert bg_jobs == []
    assert len(client.chat_calls) == 1
    assert client.chat_calls[0].get("tools") is not None

    rows = _transcript_rows(store)
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["content"] == "hello single llm"
    assert rows[1]["content"] == "sync in-turn reply"


@pytest.mark.asyncio
async def test_user_chat_multi_round_tool_calls_emit_interim_downlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        lambda **_kwargs: None,
    )

    scope = CompanionScope("sync-llm-interim", "a", str(tmp_path.resolve()))
    store = MemoryStore(scope=scope, repository=None)
    _seed_settled_workspace(store)
    interim: list[BootstrapInterimOutput] = []

    async def _sink(ev: BootstrapInterimOutput) -> None:
        interim.append(ev)

    client = _FakeInTurnSyncLLMClient(
        [
            _tool_response(
                content="working on it",
                tool_name="companion_update_prompt_slice",
                tool_arguments=json.dumps(
                    {"slice": "MEMORY", "content": "note\n"},
                    ensure_ascii=False,
                ),
            ),
            _final_response(content="done with tools"),
        ]
    )

    out = await run_companion_user_chat_turn(
        "update memory",
        deps=_user_chat_deps(store, client, bootstrap_interim_output_sink=_sink),
    )

    assert out.tool_background_started is False
    assert out.assistant_text == "done with tools"
    assert len(interim) == 1
    assert interim[0].text == "working on it"
    assert interim[0].had_tool_calls is True
    assert interim[0].user_msg_uuid == out.user_msg_uuid

    rows = _transcript_rows(store)
    assert [row["role"] for row in rows] == ["user", "assistant", "assistant"]
    assert rows[1]["content"] == "working on it"
    assert rows[2]["content"] == "done with tools"
