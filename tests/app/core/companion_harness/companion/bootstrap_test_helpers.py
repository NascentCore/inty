"""Shared test fixtures for queue-serving bootstrap ``USER_CHAT_BOOTSTRAP`` turns."""

from __future__ import annotations

import json
import threading
import uuid
from typing import Any

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputQueue,
    OutputQueueAppendInput,
    ReadyOutputMessage,
    clear_output_queues_for_tests,
)
from app.core.companion_harness.agentic_companion.types import UserMessageBatch
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
)


class InMemoryTestOutputQueue(OutputQueue):
    """``OutputQueue`` that appends to the in-memory ready buffer only (no Postgres)."""

    def __init__(self, scope: AgentScope) -> None:
        super().__init__(scope=scope)
        self._next_sequence = 0

    async def append_visible_message(
        self, append_input: OutputQueueAppendInput
    ) -> ReadyOutputMessage:
        assert append_input.text.strip() != ""
        async with self._memory_lock:
            batch_id = append_input.batch_id
            if batch_id == "":
                batch_id = f"agent-initiated:{uuid.uuid4()}"
            self._next_sequence += 1
            ready = ReadyOutputMessage(
                message_id=str(uuid.uuid4()),
                batch_id=batch_id,
                kind=append_input.kind,
                text=append_input.text,
                sequence=self._next_sequence,
                message_ids=append_input.message_ids,
                tool_background_started=append_input.tool_background_started,
                generated_images=append_input.generated_images,
            )
            self._ready.append(ready)
        return ready


def mark_interactive_bootstrap_completed(store: MemoryStore) -> None:
    """Mark ``context.json`` bootstrap complete so settled ``USER_CHAT`` track applies."""
    raw = store.read_document_if_exists(CONTEXT_JSON_REL)
    data = json.loads(raw) if raw and str(raw).strip() else {}
    assert isinstance(data, dict)
    data["workspace_bootstrap_user_interactive_completed"] = True
    store.write_document(
        CONTEXT_JSON_REL, json.dumps(data, ensure_ascii=False) + "\n"
    )


def bootstrap_queue_for_companion_scope(
    companion_scope: CompanionScope,
) -> InMemoryTestOutputQueue:
    clear_output_queues_for_tests()
    agent_scope = AgentScope(
        user_id=companion_scope.user_id,
        agent_id=companion_scope.companion_id,
    )
    return InMemoryTestOutputQueue(agent_scope)


def bootstrap_user_message_batch(
    *,
    batch_id: str | None = None,
    message_id: str | None = None,
) -> tuple[UserMessageBatch, str]:
    user_msg_id = message_id or str(uuid.uuid4())
    batch = UserMessageBatch(
        batch_id=batch_id or str(uuid.uuid4()),
        message_ids=(user_msg_id,),
    )
    return batch, user_msg_id


def bootstrap_queue_turn_deps(
    store: MemoryStore,
    llm_client: Any,
    *,
    bootstrap_interim_output_sink: Any = None,
    preset_user_msg_uuid: str | None = None,
) -> CompanionTurnDeps:
    """``CompanionTurnDeps`` with in-memory OutputQueue for bootstrap AgenticLoop turns."""
    output_queue = bootstrap_queue_for_companion_scope(store.scope)
    user_batch, default_user_msg_id = bootstrap_user_message_batch()
    tool_bg_idle = threading.Event()
    tool_bg_idle.set()
    return CompanionTurnDeps(
        store=store,
        llm_client=llm_client,
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=False,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        background_output_sink=None,
        preset_user_msg_uuid=preset_user_msg_uuid or default_user_msg_id,
        langsmith_parent_run_enabled=False,
        tool_bg_idle_event=tool_bg_idle,
        bootstrap_interim_output_sink=bootstrap_interim_output_sink,
        agentic_output_queue=output_queue,
        user_message_batch=user_batch,
    )
