"""Settled USER_CHAT with in_turn_single_llm config uses sync in-turn tool loop."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import run_companion_user_chat_turn
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.utils.config import CompanionMemoryBootstrapType, UserTurnLlmLoopMode
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


def _patch_in_turn_single_llm():
    agent = SimpleNamespace(
        companion_harness=SimpleNamespace(
            user_turn=SimpleNamespace(
                llm_loop_mode=UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM
            )
        )
    )
    return patch(
        "app.core.companion_harness.companion.turn_routes.global_config_loaded_from_config_yaml",
        SimpleNamespace(agent=agent),
    )


def _final_response(*, content: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


class _FakeInTurnSyncLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self.chat_calls: list[dict[str, Any]] = []

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        self.chat_calls.append(kwargs)
        return _final_response(content="sync in-turn reply")


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
        bootstrap_interim_output_sink=None,
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

    with _patch_in_turn_single_llm():
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
