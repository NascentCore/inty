from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.companion.ai_private_prompt import (
    append_ai_private_thought,
    load_ai_private_thoughts,
)
from app.core.companion_harness.companion.models import AI_PRIVATE_SPLICE_MANIFEST_SOURCE
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import run_companion_user_chat_turn
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.core.companion_harness.llm.chat_completions import create_chat_completion_sync
from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


class _FakeUserChatClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(
            api_key="k",
            default_model=resolve_chat_text_model("m/default"),
            chat_model=resolve_chat_text_model("m/chat"),
            tool_model=resolve_chat_text_model("m/tool"),
            async_chat_front_timeout_sec=120.0,
        )

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"m/{role}")

    def chat_completion(self, **kwargs: Any) -> Any:
        env = {
            "user_facing_reply": "visible reply",
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
async def test_successful_user_chat_persists_manifest_and_surfaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(
        scope=CompanionScope("manifest", "a", tmp_path.name),
        repository=None,
    )
    for rel in ("IDENTITY.md", "SOUL.md", "STYLE.md", "USER.md", "MEMORY.md", "CHANNELS.md"):
        store.write_document(rel, f"{rel}\n")
    store.write_document("context.json", '{"context_mode":"intimate"}\n')
    store.append_jsonl_record(
        "transcript.jsonl",
        {
            "role": "user",
            "content": "earlier",
            "ts": "2026-01-02T08:00:00+00:00",
            "uuid": "user-anchor",
        },
    )
    thought = append_ai_private_thought(
        store, text="monolog to splice", after_user_msg_uuid="user-anchor"
    )
    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        lambda **kwargs: None,
    )
    import threading

    idle = threading.Event()
    idle.set()
    deps = CompanionTurnDeps(
        store=store,
        llm_client=_FakeUserChatClient(),  # type: ignore[arg-type]
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
        langsmith_parent_run_enabled=None,
        tool_bg_idle_event=idle,
        bootstrap_interim_output_sink=None,
        agentic_loop_channel=None,
    )
    result = await run_companion_user_chat_turn("hello again", deps=deps)
    assert result.assistant_text == "visible reply"
    assert load_ai_private_thoughts(store) == []
    body = store.read_document("transcript.jsonl")
    lines = [json.loads(line) for line in body.strip().splitlines()]
    manifest_rows = [
        row for row in lines if row.get("source") == AI_PRIVATE_SPLICE_MANIFEST_SOURCE
    ]
    assert len(manifest_rows) == 1
    assert manifest_rows[0]["ai_private_thought_uuids"] == [thought.uuid]
    assert lines[-1]["role"] == "assistant"
