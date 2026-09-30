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
from app.core.llms.client import (
    CompanionLLMConfig,
)
from app.core.agentic_companion.types import (
    AGENT_INITIATED_USER_MESSAGE_BATCH_PREFIX,
    synthetic_user_message_batch,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.schedule_queue import (
    scheduled_task_synthetic_user_text,
)
from app.core.companion_harness.companion.turn import (
    _run_companion_turn_core,
    run_companion_inner_tick_scheduled_turn,
)
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model
from tests.app.core.companion_harness.companion.bootstrap_test_helpers import (
    bootstrap_queue_for_companion_scope,
    bootstrap_queue_turn_deps,
    mark_interactive_bootstrap_completed,
    queue_serving_turn_deps,
    wire_test_async_llm_client,
)
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    companion_llm_client_with_scripted_transport,
    scripted_harness_llm_config,
    with_scripted_user_turn_llm_loop_mode,
)
from app.external_services.fakes.openai import fake_step_text


class _FakeLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self.calls: list[dict[str, Any]] = []

    def sync_client_for_route(self, _route: str) -> object:
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
        msg = SimpleNamespace(
            content=json.dumps(
                {"output_to_user": True, "message": "inner reply"}
            ),
            tool_calls=[],
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def complete_text(
        self, messages: list[dict[str, Any]], *, model_role: str = "memory"
    ) -> str:
        return ""


def _seed_workspace(store: MemoryStore) -> None:
    p = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    store.write_document(p.identity, "identity")
    store.write_document(p.soul, "soul")
    store.write_document(p.user_md, "user")
    store.write_document(p.memory_md, "memory")


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
            deps=queue_serving_turn_deps(store, client),
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
        for line in store.read_document(
            DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript
        ).strip().splitlines()
    ]
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == scheduled_text
    assert rows[0]["inner_tick_kind"] == "scheduled"
    assert "proactive_chat" not in rows[0]


def _seed_bootstrap_workspace(store: MemoryStore) -> None:
    store.write_document(
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.context_json,
        json.dumps(
            {
                "context_mode": "unspecific",
                "workspace_bootstrap_user_interactive_completed": False,
            }
        ),
    )
    _seed_workspace(store)


@pytest.mark.asyncio
async def test_bootstrap_without_queue_raises_runtime_error(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("turn-bootstrap-no-queue", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    client, _ = companion_llm_client_with_scripted_transport(
        scripted_harness_llm_config(),
        (fake_step_text("bootstrap reply"),),
    )
    output_queue = bootstrap_queue_for_companion_scope(scope)
    with pytest.raises(RuntimeError, match="#3466"):
        await _run_companion_turn_core(
            "bootstrap hello",
            track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            deps=CompanionTurnDeps(
                store=store,
                llm_client=client,
                transcript_compaction=None,
                transcript_llm_window_max_messages=None,
                repository_only_store_text=False,
                runtime_context=TurnRuntimeContext(
                    channel=ChannelKind.APP_WS,
                    implicit_signal_bundle=None,
                ),
                preset_user_msg_uuid=None,
                langsmith_parent_run_enabled=False,
                tool_bg_idle_event=None,
                agentic_output_queue=output_queue,
                user_message_batch=None,
            ),
        )


@pytest.mark.asyncio
async def test_bootstrap_rejects_agent_initiated_synthetic_batch(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("turn-bootstrap-synthetic", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    client, _ = companion_llm_client_with_scripted_transport(
        scripted_harness_llm_config(),
        (fake_step_text("bootstrap reply"),),
    )
    output_queue = bootstrap_queue_for_companion_scope(scope)
    synthetic_batch = synthetic_user_message_batch(
        user_msg_uuid="preset-bootstrap-uid",
        track_label=CompanionTurnTrack.USER_CHAT.value,
    )
    with pytest.raises(RuntimeError, match="#3466"):
        await _run_companion_turn_core(
            "bootstrap hello",
            track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            deps=CompanionTurnDeps(
                store=store,
                llm_client=client,
                transcript_compaction=None,
                transcript_llm_window_max_messages=None,
                repository_only_store_text=False,
                runtime_context=TurnRuntimeContext(
                    channel=ChannelKind.APP_WS,
                    implicit_signal_bundle=None,
                ),
                preset_user_msg_uuid="preset-bootstrap-uid",
                langsmith_parent_run_enabled=False,
                tool_bg_idle_event=None,
                agentic_output_queue=output_queue,
                user_message_batch=synthetic_batch,
            ),
        )


@pytest.mark.asyncio
async def test_user_chat_direct_turn_still_synthesizes_batch(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("turn-user-chat-direct", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    mark_interactive_bootstrap_completed(store)
    client, _ = companion_llm_client_with_scripted_transport(
        scripted_harness_llm_config(),
        (fake_step_text("settled reply"),),
    )
    wire_test_async_llm_client(client)
    output_queue = bootstrap_queue_for_companion_scope(scope)
    tool_bg_idle = threading.Event()
    tool_bg_idle.set()
    deps = CompanionTurnDeps(
        store=store,
        llm_client=client,
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=False,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        preset_user_msg_uuid=None,
        langsmith_parent_run_enabled=False,
        tool_bg_idle_event=tool_bg_idle,
        agentic_output_queue=output_queue,
        user_message_batch=None,
    )
    with with_scripted_user_turn_llm_loop_mode(
        UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM
    ):
        out = await _run_companion_turn_core(
            "hello direct",
            track=CompanionTurnTrack.USER_CHAT,
            deps=deps,
        )
    assert out.assistant_text == "settled reply"
    ready = await output_queue.pull_ready_batch()
    assert ready is not None
    assert ready[0].batch_id.startswith(
        AGENT_INITIATED_USER_MESSAGE_BATCH_PREFIX
    )
    assert CompanionTurnTrack.USER_CHAT.value in ready[0].batch_id


@pytest.mark.asyncio
async def test_bootstrap_queue_turn_persists_single_user_row(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("turn-bootstrap-queue", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    client, _ = companion_llm_client_with_scripted_transport(
        scripted_harness_llm_config(),
        (fake_step_text("bootstrap reply"),),
    )
    deps = bootstrap_queue_turn_deps(store, client)
    out = await _run_companion_turn_core(
        "bootstrap hello",
        track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        deps=deps,
    )
    rows = [
        json.loads(line)
        for line in store.read_document(
            DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript
        ).splitlines()
        if line
    ]
    user_rows = [row for row in rows if row["role"] == "user"]
    assert len(user_rows) == 1
    assert user_rows[0]["content"] == "bootstrap hello"
    assert user_rows[0]["uuid"] == out.user_msg_uuid
    assert [row["role"] for row in rows] == ["user", "assistant"]
