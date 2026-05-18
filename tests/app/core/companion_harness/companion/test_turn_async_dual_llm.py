"""Async foreground chat + background tool path (kernel)."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from app.core.companion_harness.llm.chat_completions import create_chat_completion_sync
from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.models import InnerTickMode
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.tools.companion_tools import build_openai_repl_tools_inner_tick
from app.core.companion_harness.companion.turn import (
    CHAT_TRACK_RESPONSE_MESSAGE_TITLE,
    run_turn,
)
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


def _store(p: Path):
    return MemoryStore(
        scope=CompanionScope("adllm", "a", str(p.resolve())),
        repository=None,
    )


def _idle_tool_bg() -> threading.Event:
    ev = threading.Event()
    ev.set()
    return ev


def _assert_no_adjacent_user_roles(messages: list[dict[str, Any]]) -> None:
    roles = [m.get("role") for m in messages]
    for i in range(len(roles) - 1):
        assert not (
            roles[i] == "user" and roles[i + 1] == "user"
        ), f"adjacent user roles at index {i}"


class _FakeAsyncDualLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(
            api_key="k",
            default_model=resolve_chat_text_model("m/default"),
            chat_model=resolve_chat_text_model("m/chat"),
            tool_model=resolve_chat_text_model("m/tool"),
            async_chat_front_timeout_sec=120.0,
        )
        self.chat_calls: list[dict[str, Any]] = []

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"m/{role}")

    def chat_completion(self, **kwargs: Any) -> Any:
        self.chat_calls.append(kwargs)
        env = {
            "user_facing_reply": "foreground ok",
            "importance_round": 5,
            "importance_user_message": 5,
            "importance_assistant_message": 5,
        }
        msg = SimpleNamespace(
            content=json.dumps(env),
            tool_calls=[],
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def sync_client_for_route(self, route: str) -> object:
        return object()

    @property
    def chat_completions_sync(self):
        return create_chat_completion_sync

    def complete_text(
        self, messages: list[dict[str, Any]], *, model_role: str = "memory"
    ) -> str:
        return ""


@pytest.mark.asyncio
async def test_async_dual_calls_foreground_chat_without_tools_and_starts_background(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = asyncio.get_running_loop()
    store = _store(tmp_path)
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("transcript.jsonl", "")

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClient()
    out = await run_turn(
        "hello async dual",
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        defer_memory_update=True,
        memory_config=None,
        tool_bg_idle_event=_idle_tool_bg(),
    )

    assert out.tool_background_started is True
    assert out.assistant_text == "foreground ok"
    assert len(client.chat_calls) == 1
    assert client.chat_calls[0].get("tools") is None
    fg_msgs = client.chat_calls[0]["messages"]
    fg_system = [m for m in fg_msgs if m.get("role") == "system"]
    assert len(fg_system) >= 2, "foreground chat should use multiple system messages (not one concatenated block)"
    assert any(str(m.get("content") or "").strip() == "id" for m in fg_system)
    assert any(str(m.get("content") or "").strip() == "s" for m in fg_system)
    assert len(bg_jobs) == 1
    assert bg_jobs[0]["chat_completions_sync"] is client.chat_completions_sync
    bg_msgs = bg_jobs[0]["request_messages"]
    bg_system = [m for m in bg_msgs if m.get("role") == "system"]
    assert len(bg_system) >= 2, "background tool path should use multiple system messages"
    assert bg_jobs[0]["tool_model"].id_on_provider == "m/tool"
    assert bg_jobs[0]["main_event_loop"] is loop
    assert bg_jobs[0]["force_tools_first_round"] is False
    _assert_no_adjacent_user_roles(bg_msgs)
    assert bg_msgs[-1] == {
        "role": "assistant",
        "content": f"{CHAT_TRACK_RESPONSE_MESSAGE_TITLE}\n\nforeground ok",
    }


@pytest.mark.asyncio
async def test_async_dual_inner_tick_passes_tick_context_and_inner_tick_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = asyncio.get_running_loop()
    store = _store(tmp_path)
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("transcript.jsonl", "")

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClient()
    await run_turn(
        "ignored for inner tick",
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        defer_memory_update=True,
        memory_config=None,
        inner_tick_turn=True,
        inner_tick_mode=InnerTickMode.MAINTENANCE,
    )

    assert len(client.chat_calls) == 0
    assert len(bg_jobs) == 1
    job = bg_jobs[0]
    assert job["inner_tick_turn"] is True
    assert job["inner_tick_mode"] == InnerTickMode.MAINTENANCE
    assert job["implicit_signal_bundle"] is None
    assert job["main_event_loop"] is loop
    expected = {t["function"]["name"] for t in build_openai_repl_tools_inner_tick()}
    got = {t["function"]["name"] for t in job["tools"]}
    assert got == expected
    assert "generate_image" not in got
    bg_msgs = job["request_messages"]
    assert job["force_tools_first_round"] is True
    _assert_no_adjacent_user_roles(bg_msgs)
    assert bg_msgs[-1].get("role") != "assistant"


@pytest.mark.asyncio
async def test_proactive_inner_tick_heartbeat_sync_still_calls_llm(
    tmp_path: Path,
) -> None:
    """PROACTIVE inner tick is HEARTBEAT_SYNC (no async dual branch); no foreground skip."""
    store = _store(tmp_path)
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("transcript.jsonl", "")

    client = _FakeAsyncDualLLMClient()
    await run_turn(
        "ignored",
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        defer_memory_update=True,
        memory_config=None,
        inner_tick_turn=True,
        inner_tick_mode=InnerTickMode.PROACTIVE_CHAT,
    )

    assert len(client.chat_calls) == 1


class _FakeAsyncDualLLMClientEmptyFg:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(
            api_key="k",
            default_model=resolve_chat_text_model("m/default"),
            chat_model=resolve_chat_text_model("m/chat"),
            tool_model=resolve_chat_text_model("m/tool"),
            async_chat_front_timeout_sec=120.0,
        )
        self.chat_calls: list[dict[str, Any]] = []

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"m/{role}")

    def chat_completion(self, **kwargs: Any) -> Any:
        self.chat_calls.append(kwargs)
        env = {
            "user_facing_reply": "",
            "importance_round": 5,
            "importance_user_message": 5,
            "importance_assistant_message": 5,
        }
        msg = SimpleNamespace(
            content=json.dumps(env),
            tool_calls=[],
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def sync_client_for_route(self, route: str) -> object:
        return object()

    @property
    def chat_completions_sync(self):
        return create_chat_completion_sync

    def complete_text(
        self, messages: list[dict[str, Any]], *, model_role: str = "memory"
    ) -> str:
        return ""


@pytest.mark.asyncio
async def test_async_dual_empty_user_facing_reply_keeps_required_and_skips_inject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("transcript.jsonl", "")

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClientEmptyFg()
    await run_turn(
        "hello empty fg",
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        defer_memory_update=True,
        memory_config=None,
        tool_bg_idle_event=_idle_tool_bg(),
    )

    assert len(bg_jobs) == 1
    bg_msgs = bg_jobs[0]["request_messages"]
    assert bg_jobs[0]["force_tools_first_round"] is True
    assert bg_msgs[-1].get("role") != "assistant"
