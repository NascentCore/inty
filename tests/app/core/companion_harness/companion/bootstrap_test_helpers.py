"""Shared test fixtures for queue-serving companion turns (bootstrap and settled)."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from dataclasses import replace
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


class _TestAsyncLlmClientAdapter:
    """Minimal ``AsyncLlmClient`` stand-in delegating to a sync test double."""

    def __init__(self, sync_client: Any) -> None:
        self._sync = sync_client

    @property
    def config(self) -> Any:
        return self._sync.config

    def resolve_model(self, role: str) -> Any:
        return self._sync.resolve_model(role)

    async def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        model: Any = None,
        response_format: dict[str, Any] | None = None,
        scene: Any = None,
        langsmith_extra: dict[str, Any] | None = None,
        high_reasoning: bool = False,
    ) -> Any:
        _ = scene
        kw: dict[str, Any] = {"messages": messages}
        if model is not None:
            kw["model"] = model
        if tools is not None:
            kw["tools"] = tools
        if tool_choice is not None:
            kw["tool_choice"] = tool_choice
        if response_format is not None:
            kw["response_format"] = response_format
        if langsmith_extra is not None:
            kw["langsmith_extra"] = langsmith_extra
        if high_reasoning:
            kw["high_reasoning"] = high_reasoning
        if hasattr(self._sync, "chat_completion"):
            return await asyncio.to_thread(self._sync.chat_completion, **kw)
        raise AssertionError("sync test client missing chat_completion")

    async def chat_completion_with_retrial(
        self,
        *,
        messages: list[dict[str, Any]],
        model: Any,
        tools: list[Any] | None,
        tool_choice: str | None,
        response_format: dict[str, Any] | None,
        scene: Any,
        langsmith_extra: dict[str, Any] | None,
        high_reasoning: bool,
        max_attempts: int,
        per_attempt_timeout_sec: float,
        trace_id: str | None,
        attempt_log_label: str,
    ) -> Any:
        sync_retrial = getattr(self._sync, "chat_completion_with_retrial", None)
        if sync_retrial is not None:
            if asyncio.iscoroutinefunction(sync_retrial):
                return await sync_retrial(
                    messages=messages,
                    model=model,
                    tools=tools,
                    tool_choice=tool_choice,
                    response_format=response_format,
                    scene=scene,
                    langsmith_extra=langsmith_extra,
                    high_reasoning=high_reasoning,
                    max_attempts=max_attempts,
                    per_attempt_timeout_sec=per_attempt_timeout_sec,
                    trace_id=trace_id,
                    attempt_log_label=attempt_log_label,
                )
            return await asyncio.to_thread(
                sync_retrial,
                messages=messages,
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                scene=scene,
                langsmith_extra=langsmith_extra,
                high_reasoning=high_reasoning,
                max_attempts=max_attempts,
                per_attempt_timeout_sec=per_attempt_timeout_sec,
                trace_id=trace_id,
                attempt_log_label=attempt_log_label,
            )
        _ = trace_id
        _ = attempt_log_label
        assert max_attempts >= 1
        return await asyncio.wait_for(
            self.chat_completion(
                messages=messages,
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                scene=scene,
                langsmith_extra=langsmith_extra,
                high_reasoning=high_reasoning,
            ),
            timeout=per_attempt_timeout_sec,
        )


def wire_test_async_llm_client(llm_client: Any) -> None:
    """Attach ``async_llm_client`` to plain sync test doubles used by turn tests."""
    if getattr(llm_client, "async_llm_client", None) is not None:
        return
    setattr(
        llm_client, "async_llm_client", _TestAsyncLlmClientAdapter(llm_client)
    )


def queue_serving_turn_deps(
    store: MemoryStore,
    llm_client: Any,
    *,
    preset_user_msg_uuid: str | None = None,
    user_message_batch: UserMessageBatch | None = None,
    **overrides: object,
) -> CompanionTurnDeps:
    """``CompanionTurnDeps`` with in-memory ``OutputQueue`` for AgenticLoop turns."""
    wire_test_async_llm_client(llm_client)
    output_queue = bootstrap_queue_for_companion_scope(store.scope)
    user_batch, default_user_msg_id = bootstrap_user_message_batch()
    resolved_batch = user_message_batch or user_batch
    tool_bg_idle = threading.Event()
    tool_bg_idle.set()
    deps = CompanionTurnDeps(
        store=store,
        llm_client=llm_client,
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=False,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        preset_user_msg_uuid=preset_user_msg_uuid or default_user_msg_id,
        langsmith_parent_run_enabled=False,
        tool_bg_idle_event=tool_bg_idle,
        agentic_output_queue=output_queue,
        user_message_batch=resolved_batch,
    )
    if overrides:
        return replace(deps, **overrides)
    return deps


def bootstrap_queue_turn_deps(
    store: MemoryStore,
    llm_client: Any,
    *,
    preset_user_msg_uuid: str | None = None,
) -> CompanionTurnDeps:
    """``CompanionTurnDeps`` with in-memory OutputQueue for bootstrap AgenticLoop turns."""
    return queue_serving_turn_deps(
        store,
        llm_client,
        preset_user_msg_uuid=preset_user_msg_uuid,
    )
