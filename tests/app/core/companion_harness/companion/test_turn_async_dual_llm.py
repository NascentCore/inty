"""Async foreground chat + background tool path (kernel)."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.llm.chat_completions import (
    create_chat_completion_sync,
)
from app.core.llms.client import CompanionLLMConfig
from app.core.companion_harness.companion.models import (
    InnerTickActivity,
    load_transcript_from_store,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
    TRANSCRIPT_JSONL_REL,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_repl_tools_inner_tick,
    build_openai_repl_tools_inner_tick_autonomy,
)
from app.core.companion_harness.companion.dual_llm_foreground_chat import (
    build_chat_track_handoff_assistant_message,
)
from app.core.companion_harness.companion.turn import (
    run_companion_inner_tick_monolog_turn,
    run_companion_inner_tick_proactive_chat_turn,
    run_companion_user_chat_turn,
    run_inner_tick_autonomy,
)
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


def _default_turn_deps(
    store: MemoryStore,
    llm_client: object,
    **overrides: object,
) -> CompanionTurnDeps:
    deps = CompanionTurnDeps(
        store=store,
        llm_client=llm_client,  # type: ignore[arg-type]
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=False,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        background_output_sink=None,
        preset_user_msg_uuid=None,
        langsmith_parent_run_enabled=None,
        tool_bg_idle_event=None,
        bootstrap_interim_output_sink=None,
    )
    if overrides:
        from dataclasses import replace

        return replace(deps, **overrides)
    return deps


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
    def __init__(self, *, turn_recall: str = "") -> None:
        self.turn_recall = turn_recall
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
            "output_to_user": True,
            "turn_recall": self.turn_recall,
        }
        msg = SimpleNamespace(
            content=json.dumps(env),
            tool_calls=[],
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def sync_client_for_route(self, _route: str) -> object:
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
    store.write_document(CONTEXT_JSON_REL, '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document(TRANSCRIPT_JSONL_REL, "")

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClient()
    out = await run_companion_user_chat_turn(
        "hello async dual",
        deps=_default_turn_deps(
            store,
            client,
            tool_bg_idle_event=_idle_tool_bg(),
        ),
    )

    assert out.tool_background_started is True
    assert out.assistant_text == "foreground ok"
    assert len(client.chat_calls) == 1
    assert client.chat_calls[0].get("tools") is None
    fg_msgs = client.chat_calls[0]["messages"]
    fg_system = [m for m in fg_msgs if m.get("role") == "system"]
    assert (
        len(fg_system) >= 2
    ), "foreground chat should use multiple system messages (not one concatenated block)"
    assert any(str(m.get("content") or "").strip() == "id" for m in fg_system)
    assert any(str(m.get("content") or "").strip() == "s" for m in fg_system)
    assert len(bg_jobs) == 1
    assert bg_jobs[0]["chat_completions_sync"] is client.chat_completions_sync
    bg_msgs = bg_jobs[0]["request_messages"]
    bg_system = [m for m in bg_msgs if m.get("role") == "system"]
    assert (
        len(bg_system) >= 2
    ), "background tool path should use multiple system messages"
    assert bg_jobs[0]["tool_model"].id_on_provider == "m/tool"
    assert bg_jobs[0]["main_event_loop"] is loop
    assert bg_jobs[0]["force_tools_first_round"] is False
    _assert_no_adjacent_user_roles(bg_msgs)
    assert bg_msgs[-1] == build_chat_track_handoff_assistant_message(
        fg_text="foreground ok"
    )


@pytest.mark.asyncio
async def test_async_dual_run_turn_persists_turn_recall_on_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    store.write_document(CONTEXT_JSON_REL, '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("STYLE.md", "st\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("CHANNELS.md", "ch\n")
    store.write_document("COMPANIONSHIP.md", "bond\n")
    store.write_document(TRANSCRIPT_JSONL_REL, "")

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        lambda **_kwargs: None,
    )

    client = _FakeAsyncDualLLMClient(turn_recall="用户提到下周见面")
    out = await run_companion_user_chat_turn(
        "hello",
        deps=_default_turn_deps(
            store,
            client,
            tool_bg_idle_event=_idle_tool_bg(),
        ),
    )

    assert out.turn_recall == "用户提到下周见面"
    msgs = load_transcript_from_store(store, TRANSCRIPT_JSONL_REL)
    assistant_rows = [m for m in msgs if m.role == "assistant"]
    assert len(assistant_rows) == 1
    assert assistant_rows[0].turn_recall == "用户提到下周见面"
    assert assistant_rows[0].content == "foreground ok"


@pytest.mark.asyncio
async def test_async_dual_inner_tick_passes_tick_context_and_inner_tick_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = asyncio.get_running_loop()
    store = _store(tmp_path)
    store.write_document(CONTEXT_JSON_REL, '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document(TRANSCRIPT_JSONL_REL, "")

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClient()
    await run_companion_inner_tick_monolog_turn(
        deps=_default_turn_deps(store, client),
    )

    assert len(client.chat_calls) == 0
    assert len(bg_jobs) == 1
    job = bg_jobs[0]
    assert job["inner_tick_turn"] is True
    assert job["inner_tick_activity"] == InnerTickActivity.MONOLOG
    assert job["runtime_context"].implicit_signal_bundle is None
    assert job["main_event_loop"] is loop
    expected = {
        t["function"]["name"] for t in build_openai_repl_tools_inner_tick()
    }
    got = {t["function"]["name"] for t in job["tools"]}
    assert got == expected
    assert "generate_image" not in got
    bg_msgs = job["request_messages"]
    assert job["force_tools_first_round"] is True
    _assert_no_adjacent_user_roles(bg_msgs)
    assert bg_msgs[-1].get("role") != "assistant"


@pytest.mark.asyncio
async def test_async_dual_inner_tick_autonomy_uses_autonomy_system_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    store.write_document(CONTEXT_JSON_REL, '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document(TRANSCRIPT_JSONL_REL, "")

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClient()
    await run_inner_tick_autonomy(
        deps=_default_turn_deps(store, client),
    )

    assert len(client.chat_calls) == 0
    assert len(bg_jobs) == 1
    job = bg_jobs[0]
    assert job["inner_tick_turn"] is True
    assert job["inner_tick_activity"] == InnerTickActivity.AUTONOMY
    expected = {
        t["function"]["name"]
        for t in build_openai_repl_tools_inner_tick_autonomy()
    }
    got = {t["function"]["name"] for t in job["tools"]}
    assert got == expected
    assert "generate_image" in got
    bg_system = [
        str(m.get("content") or "")
        for m in job["request_messages"]
        if m.get("role") == "system"
    ]
    autonomy_blocks = [
        c for c in bg_system if c.startswith("本轮（AUTONOMY 自主活动）")
    ]
    monolog_blocks = [c for c in bg_system if c.startswith("本轮（内在节拍）")]
    ai_private_blocks = [
        c for c in bg_system if c.startswith("内在活动（ai_private）")
    ]
    assert len(autonomy_blocks) == 1
    assert monolog_blocks == []
    assert ai_private_blocks == []


@pytest.mark.asyncio
async def test_proactive_inner_tick_proactive_chat_sync_still_calls_llm(
    tmp_path: Path,
) -> None:
    """PROACTIVE inner tick is PROACTIVE_CHAT_SYNC (no async dual branch); no foreground skip."""
    store = _store(tmp_path)
    store.write_document(CONTEXT_JSON_REL, '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document(TRANSCRIPT_JSONL_REL, "")

    client = _FakeAsyncDualLLMClient()
    await run_companion_inner_tick_proactive_chat_turn(
        deps=_default_turn_deps(store, client),
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

    def sync_client_for_route(self, _route: str) -> object:
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
    store.write_document(CONTEXT_JSON_REL, '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document(TRANSCRIPT_JSONL_REL, "")

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClientEmptyFg()
    await run_companion_user_chat_turn(
        "hello empty fg",
        deps=_default_turn_deps(
            store,
            client,
            tool_bg_idle_event=_idle_tool_bg(),
        ),
    )

    assert len(bg_jobs) == 1
    bg_msgs = bg_jobs[0]["request_messages"]
    assert bg_jobs[0]["force_tools_first_round"] is True
    assert bg_msgs[-1].get("role") != "assistant"
