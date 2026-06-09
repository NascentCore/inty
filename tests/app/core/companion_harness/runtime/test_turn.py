from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.llm.chat_completions import create_chat_completion_sync
from app.core.companion_harness.companion.llm_client import (
    LLM_SCENE_CHAT,
    CompanionLLMConfig,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.proactive_chat import (
    PROACTIVE_CHAT_SYNTHETIC_SYSTEM_MESSAGE,
)
from app.core.companion_harness.runtime.models import (
    INNER_TICK_SYNTHETIC_USER_TEXT,
    InnerTickActivity,
)
from app.core.companion_harness.runtime.scope import CompanionScope
from app.core.companion_harness.companion.schedule_queue import (
    scheduled_task_synthetic_user_text,
)
from app.core.companion_harness.runtime.turn import (
    run_companion_inner_tick_scheduled_turn
)
from app.core.companion_harness.runtime.turn_deps import CompanionTurnDeps
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.user_time_context_llm_slice import (
    build_companion_user_time_context_system_content,
)
from app.schemas.chat import UserTimeContext
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


class _FakeLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self.calls: list[dict[str, Any]] = []

    def sync_client_for_route(self, route: str) -> object:
        return object()

    @property
    def chat_completions_sync(self):
        return create_chat_completion_sync

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

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


def test_run_turn_inner_tick_scheduled_semantics(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("turn-t", "a", f"it-sched-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _FakeLLMClient()
    scheduled_text = scheduled_task_synthetic_user_text(
        task_text="吃药",
        exec_time_utc="2026-05-19T08:00:00Z",
    )

    out = asyncio.run(
        run_companion_inner_tick_scheduled_turn(
            scheduled_text,
            deps=CompanionTurnDeps(
                store=store,
                llm_client=client,  # type: ignore[arg-type]
                transcript_compaction=None,
                transcript_llm_window_max_messages=None,
                repository_only_store_text=False,
                memory_bootstrap_type="NONE",
                runtime_context=TurnRuntimeContext(
                    channel=CompanionRuntimeChannel.APP,
                    implicit_signal_bundle=None,
                ),
                background_output_sink=None,
                preset_user_msg_uuid=None,
                langsmith_parent_run_enabled=False,
                tool_bg_idle_event=None,
                bootstrap_interim_output_sink=None,
            ),
        )
    )

    assert out.assistant_text == "inner reply"
    assert out.inner_tick_activity == "proactive_chat"
    llm_msgs = client.calls[0]["messages"]
    assert llm_msgs[-1]["role"] == "user"
    user_tail = llm_msgs[-1]["content"] or ""
    assert "提醒事项" in user_tail
    assert scheduled_text in user_tail
    assert user_tail.startswith("[")
    assert user_tail.endswith(f"] {scheduled_text}")
    assert "[SYSTEM PROACTIVE CHAT]" not in user_tail
    assert out.transcript_user_content == scheduled_text

    rows = [
        json.loads(line)
        for line in store.read_document("transcript.jsonl").strip().splitlines()
    ]
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == scheduled_text
    assert rows[0]["inner_tick"] is True
    assert rows[0]["scheduled"] is True
    assert rows[0].get("proactive_chat") is not True
