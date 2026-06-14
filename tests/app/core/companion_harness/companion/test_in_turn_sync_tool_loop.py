"""Tests for public ``run_in_turn_sync_tool_loop`` entry."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    InTurnSyncToolLoopInput,
    run_in_turn_sync_tool_loop,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)
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


class _FakeSyncToolLoopLLMClient:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self._responses = iter(responses)
        self.tools_per_call: list[tuple[dict[str, Any], ...]] = []

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        tools = kwargs.get("tools")
        self.tools_per_call.append(
            tuple(tools) if tools is not None else ()
        )
        return next(self._responses)


def _transcript_rows(store: MemoryStore) -> list[dict[str, Any]]:
    body = store.read_document("transcript.jsonl")
    assert body is not None
    return [json.loads(line) for line in body.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_run_in_turn_sync_tool_loop_user_before_assistant_transcript(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("in-turn-sync", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    client = _FakeSyncToolLoopLLMClient([_final_response(content="done")])

    result = await run_in_turn_sync_tool_loop(
        InTurnSyncToolLoopInput(
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            messages=({"role": "user", "content": "hi"},),
            tools_for_turn=(),
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
            langsmith_foreground_source=SOURCE_BOOTSTRAP_TRACK,
            repository_only_store_text=False,
            trace_id="trace-1",
            user_text="hi",
            ts_user=datetime(2026, 1, 1, tzinfo=timezone.utc),
            user_msg_uuid="user-uuid-1",
            transcript_rel="transcript.jsonl",
            interim_output_sink=None,
            langsmith_slice=CompanionTurnLangsmithSlice.from_runtime_context(
                TurnRuntimeContext(
                    channel=CompanionRuntimeChannel.APP,
                    implicit_signal_bundle=None,
                )
            ),
            max_tool_rounds=4,
            after_tool_messages_appended=None,
        )
    )

    rows = _transcript_rows(store)
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["uuid"] == "user-uuid-1"
    assert rows[1]["reply_to"] == "user-uuid-1"
    assert result.assistant_text == "done"
    assert result.skip_final_transcript_assistant_row is True


@pytest.mark.asyncio
async def test_run_in_turn_sync_tool_loop_interim_sink_on_tool_round(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("in-turn-sync-interim", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    store.write_document("IDENTITY.md", "IDENTITY\n")
    interim: list[BootstrapInterimOutput] = []

    async def _sink(ev: BootstrapInterimOutput) -> None:
        interim.append(ev)

    client = _FakeSyncToolLoopLLMClient(
        [
            _tool_response(
                content="interim line",
                tool_name="memory_store_write_document",
                tool_arguments=json.dumps(
                    {"relative_path": "IDENTITY.md", "content": "x\n"},
                    ensure_ascii=False,
                ),
            ),
            _final_response(content="terminal line"),
        ]
    )

    result = await run_in_turn_sync_tool_loop(
        InTurnSyncToolLoopInput(
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            messages=({"role": "user", "content": "go"},),
            tools_for_turn=(
                {
                    "type": "function",
                    "function": {
                        "name": "memory_store_write_document",
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
            ),
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
            langsmith_foreground_source=SOURCE_BOOTSTRAP_TRACK,
            repository_only_store_text=False,
            trace_id="trace-2",
            user_text="go",
            ts_user=datetime(2026, 1, 2, tzinfo=timezone.utc),
            user_msg_uuid="user-uuid-2",
            transcript_rel="transcript.jsonl",
            interim_output_sink=_sink,
            langsmith_slice=CompanionTurnLangsmithSlice.from_runtime_context(
                TurnRuntimeContext(
                    channel=CompanionRuntimeChannel.APP,
                    implicit_signal_bundle=None,
                )
            ),
            max_tool_rounds=4,
            after_tool_messages_appended=None,
        )
    )

    rows = _transcript_rows(store)
    assert [row["role"] for row in rows] == ["user", "assistant", "assistant"]
    assert rows[1]["content"] == "interim line"
    assert rows[2]["content"] == "terminal line"
    assert len(interim) == 1
    assert interim[0].text == "interim line"
    assert interim[0].had_tool_calls is True
    assert result.assistant_text == "terminal line"
    assert result.skip_final_transcript_assistant_row is True


@pytest.mark.asyncio
async def test_run_bootstrap_track_sync_tool_loop_returns_result(
    tmp_path: Path,
) -> None:
    from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
        BootstrapInTurnSyncToolLoopInput,
        InTurnSyncToolLoopResult,
        run_bootstrap_track_sync_tool_loop,
    )

    scope = CompanionScope("bootstrap-wrapper", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    client = _FakeSyncToolLoopLLMClient([_final_response(content="bootstrap ok")])

    result = await run_bootstrap_track_sync_tool_loop(
        BootstrapInTurnSyncToolLoopInput(
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            messages=({"role": "user", "content": "hi"},),
            tools_for_turn=(),
            memory_bootstrap_type="none",
            repository_only_store_text=False,
            trace_id="trace-bootstrap",
            user_text="hi",
            ts_user=datetime(2026, 1, 3, tzinfo=timezone.utc),
            user_msg_uuid="user-bootstrap",
            transcript_rel="transcript.jsonl",
            bootstrap_interim_output_sink=None,
        agentic_loop_channel=None,
            langsmith_slice=CompanionTurnLangsmithSlice.from_runtime_context(
                TurnRuntimeContext(
                    channel=CompanionRuntimeChannel.APP,
                    implicit_signal_bundle=None,
                )
            ),
        )
    )

    assert isinstance(result, InTurnSyncToolLoopResult)
    assert result.assistant_text == "bootstrap ok"


@pytest.mark.asyncio
async def test_run_in_turn_sync_tool_loop_after_tool_hook_refreshes_openai_tools(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("in-turn-sync-refresh", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    refreshed_tools = (
        {
            "type": "function",
            "function": {"name": "refreshed_tool", "parameters": {"type": "object"}},
        },
    )

    async def _refresh_tools(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], ...]:
        messages_with_tool_results.append(
            {"role": "system", "content": "refreshed stack"}
        )
        return refreshed_tools

    initial_tools = (
        {
            "type": "function",
            "function": {
                "name": "memory_store_write_document",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    )
    client = _FakeSyncToolLoopLLMClient(
        [
            _tool_response(
                content="working",
                tool_name="memory_store_write_document",
                tool_arguments=json.dumps(
                    {"relative_path": "IDENTITY.md", "content": "x\n"},
                    ensure_ascii=False,
                ),
            ),
            _final_response(content="done"),
        ]
    )

    await run_in_turn_sync_tool_loop(
        InTurnSyncToolLoopInput(
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            messages=({"role": "user", "content": "go"},),
            tools_for_turn=initial_tools,
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
            langsmith_foreground_source=SOURCE_BOOTSTRAP_TRACK,
            repository_only_store_text=False,
            trace_id="trace-refresh",
            user_text="go",
            ts_user=datetime(2026, 1, 4, tzinfo=timezone.utc),
            user_msg_uuid="user-uuid-refresh",
            transcript_rel="transcript.jsonl",
            interim_output_sink=None,
            langsmith_slice=CompanionTurnLangsmithSlice.from_runtime_context(
                TurnRuntimeContext(
                    channel=CompanionRuntimeChannel.APP,
                    implicit_signal_bundle=None,
                )
            ),
            max_tool_rounds=4,
            after_tool_messages_appended=_refresh_tools,
        )
    )

    assert client.tools_per_call[0] == initial_tools
    assert client.tools_per_call[1] == refreshed_tools
