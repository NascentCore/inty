from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.agentic_kernel.llm.chat_completions import create_chat_completion_sync
from app.core.agentic_kernel.companion.llm_client import (
    LLM_SCENE_CHAT,
    LLM_SCENE_INNER_TICK,
    CompanionLLMConfig,
)
from app.core.agentic_kernel.companion.memory_store import MemoryStore
from app.core.agentic_kernel.companion.heartbeat import (
    HEARTBEAT_SYNTHETIC_USER_TEXT,
    PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER,
)
from app.core.agentic_kernel.companion.models import (
    INNER_TICK_SYNTHETIC_USER_TEXT,
    InnerTickMode,
)
from app.core.agentic_kernel.companion.turn import run_turn
from app.schemas.chat import UserTimeContext
from app.schemas.implicit_signals import ImplicitSignalBundle


class _FakeLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self.calls: list[dict[str, Any]] = []

    def sync_client_for_route(self, route: str) -> object:
        return object()

    @property
    def chat_completions_sync(self):
        return create_chat_completion_sync

    def resolve_model(self, role: str) -> str:
        return f"test/{role}"

    def chat_completion(self, **kwargs: Any) -> Any:
        rec = dict(kwargs)
        if isinstance(rec.get("messages"), list):
            rec["messages"] = list(rec["messages"])
        self.calls.append(rec)
        msg = SimpleNamespace(content="inner reply", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def complete_text(
        self, messages: list[dict[str, Any]], *, model_role: str = "memory"
    ) -> str:
        return ""


def _seed_workspace(store: MemoryStore) -> None:
    store.write_document("IDENTITY.md", "identity")
    store.write_document("SOUL.md", "soul")
    store.write_document("USER.md", "user")
    store.write_document("MEMORY.md", "memory")


def test_run_turn_inner_tick_persists_synthetic_turn_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(workspace_root=tmp_path, repository=None)
    _seed_workspace(store)
    client = _FakeLLMClient()
    monkeypatch.setattr(
        "app.core.agentic_kernel.companion.turn.start_tool_background_job",
        lambda **kwargs: None,
    )

    out = asyncio.run(
        run_turn(
            tmp_path,
            "caller text should be replaced",
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            inner_tick_turn=True,
        )
    )

    assert out.assistant_text == "inner reply"
    assert out.tool_background_started is True
    assert client.calls[0]["scene"] == LLM_SCENE_INNER_TICK

    rows = [
        json.loads(line)
        for line in store.read_document("transcript_inner_tick.jsonl")
        .strip()
        .splitlines()
    ]
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == INNER_TICK_SYNTHETIC_USER_TEXT
    assert rows[0]["inner_tick"] is True
    assert rows[1]["role"] == "assistant"
    assert rows[1]["source"] == "inner_tick"


def test_run_turn_inner_tick_maintenance_includes_user_time_context_system_slice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``ImplicitSignalBundle.client_time`` injects User Time Context into inner-tick LLM messages."""
    store = MemoryStore(workspace_root=tmp_path, repository=None)
    _seed_workspace(store)
    client = _FakeLLMClient()
    monkeypatch.setattr(
        "app.core.agentic_kernel.companion.turn.start_tool_background_job",
        lambda **kwargs: None,
    )
    bundle = ImplicitSignalBundle(
        client_time=UserTimeContext(
            local_time="2026-05-01T08:00:00+08:00",
            timezone="Asia/Shanghai",
            utc_offset_minutes=480,
        ),
    )
    out = asyncio.run(
        run_turn(
            tmp_path,
            "ignored",
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            inner_tick_turn=True,
            inner_tick_mode=InnerTickMode.MAINTENANCE,
            implicit_signal_bundle=bundle,
        )
    )
    assert out.assistant_text == "inner reply"
    llm_msgs = client.calls[0]["messages"]
    joined = "\n".join(
        (m.get("content") or "") for m in llm_msgs if m.get("role") == "system"
    )
    assert "##User Time Context" in joined


def test_run_turn_inner_tick_proactive_chat_matches_legacy_heartbeat_semantics(
    tmp_path: Path,
) -> None:
    store = MemoryStore(workspace_root=tmp_path, repository=None)
    _seed_workspace(store)
    client = _FakeLLMClient()

    out = asyncio.run(
        run_turn(
            tmp_path,
            "caller text ignored",
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            inner_tick_turn=True,
            inner_tick_mode=InnerTickMode.PROACTIVE_CHAT,
        )
    )

    assert out.assistant_text == "inner reply"
    assert client.calls[0]["scene"] == LLM_SCENE_CHAT
    assert not client.calls[0].get("tools")
    llm_msgs = client.calls[0]["messages"]
    assert llm_msgs[-1]["role"] == "user"
    assert llm_msgs[-1]["content"] == PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER
    assert llm_msgs[-2]["role"] == "system"
    assert llm_msgs[-2]["content"] == HEARTBEAT_SYNTHETIC_USER_TEXT
    assert not any(
        m.get("role") == "user"
        and (m.get("content") or "").strip() == INNER_TICK_SYNTHETIC_USER_TEXT.strip()
        for m in llm_msgs
    )

    rows = [
        json.loads(line)
        for line in store.read_document("transcript.jsonl").strip().splitlines()
    ]
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER
    assert rows[0]["inner_tick"] is True
    assert rows[0]["heartbeat"] is True
