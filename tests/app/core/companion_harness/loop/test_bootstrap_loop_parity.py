"""Bootstrap legacy sync loop vs ``run_agentic_loop`` strict parity."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    BootstrapInTurnSyncToolLoopInput,
    run_bootstrap_track_sync_tool_loop,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
)
from app.core.companion_harness.loop.bootstrap_input import (
    BootstrapAgenticLoopBuildInput,
    build_bootstrap_agentic_loop_input,
)
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.output_queue import LoopDeliverableKind
from app.core.companion_harness.loop.parity.fixtures import (
    FakeSyncToolLoopLLMClient,
    final_response,
    tool_response,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.services.agentic_companion.channel import RecordingChannel
from tests.app.core.companion_harness.loop.test_support import (
    run_agentic_loop_with_channel,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)
from app.services.agentic_companion.downlink import DownlinkKind


def _memory_write_tool() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "memory_store_write_document",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _fresh_store(label: str) -> MemoryStore:
    store = MemoryStore(
        scope=CompanionScope("parity", "agent", label),
        repository=None,
    )
    store.write_document("transcript.jsonl", "")
    store.write_document("IDENTITY.md", "IDENTITY\n")
    store.write_document(
        "context.json",
        json.dumps(
            {"workspace_bootstrap_user_interactive_completed": False},
            ensure_ascii=False,
        )
        + "\n",
    )
    return store


def _runtime_context() -> TurnRuntimeContext:
    return TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    )


@pytest.mark.asyncio
async def test_bootstrap_loop_matches_legacy_sync_tool_loop() -> None:
    store = _fresh_store("bootstrap-parity")
    client = FakeSyncToolLoopLLMClient(
        [
            tool_response(
                content="interim body",
                tool_name="memory_store_write_document",
                tool_arguments=json.dumps(
                    {"relative_path": "IDENTITY.md", "content": "x\n"},
                    ensure_ascii=False,
                ),
            ),
            final_response(content="terminal body"),
        ]
    )
    msgs = ({"role": "user", "content": "go"},)
    tools = (_memory_write_tool(),)
    user_msg_uuid = "parity-user"
    trace_id = "parity-trace"
    ts_user = datetime(2026, 1, 1, tzinfo=timezone.utc)
    langsmith_slice = CompanionTurnLangsmithSlice.from_runtime_context(
        _runtime_context()
    )
    legacy = await run_bootstrap_track_sync_tool_loop(
        BootstrapInTurnSyncToolLoopInput(
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            messages=msgs,
            tools_for_turn=tools,
            memory_bootstrap_type="USER_INTERACTIVE",
            repository_only_store_text=False,
            trace_id=trace_id,
            user_text="go",
            ts_user=ts_user,
            user_msg_uuid=user_msg_uuid,
            transcript_rel="transcript.jsonl",
            bootstrap_interim_output_sink=None,
            langsmith_slice=langsmith_slice,
        )
    )
    store2 = _fresh_store("bootstrap-parity-loop")
    client2 = FakeSyncToolLoopLLMClient(
        [
            tool_response(
                content="interim body",
                tool_name="memory_store_write_document",
                tool_arguments=json.dumps(
                    {"relative_path": "IDENTITY.md", "content": "x\n"},
                    ensure_ascii=False,
                ),
            ),
            final_response(content="terminal body"),
        ]
    )
    channel = RecordingChannel()
    loop_out = await run_agentic_loop_with_channel(
        build_bootstrap_agentic_loop_input(
            BootstrapAgenticLoopBuildInput(
                store=store2,
                llm_client=client2,  # type: ignore[arg-type]
                openai_messages=msgs,
                openai_tools=tools,
                memory_bootstrap_type="USER_INTERACTIVE",
                repository_only_store_text=False,
                trace_id=trace_id,
                user_text="go",
                ts_user=ts_user,
                user_msg_uuid=user_msg_uuid,
                transcript_rel="transcript.jsonl",
                langsmith_slice=langsmith_slice,
                runtime_context=_runtime_context(),
            )
        ),
        llm_loop_mode=UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
        channel=channel,
    )
    assert loop_out.assistant_text == legacy.assistant_text
    assert (
        loop_out.skip_final_transcript_assistant_row
        == legacy.skip_final_transcript_assistant_row
    )
    assert loop_out.last_interim_assistant_msg_uuid is not None
    assert legacy.last_interim_assistant_msg_uuid is not None
    legacy_rows = [
        json.loads(line)
        for line in store.read_document("transcript.jsonl").splitlines()
        if line.strip()
    ]
    loop_rows = [
        json.loads(line)
        for line in store2.read_document("transcript.jsonl").splitlines()
        if line.strip()
    ]
    assert [r.get("role") for r in legacy_rows] == [r.get("role") for r in loop_rows]
    assert [r.get("content") for r in legacy_rows] == [
        r.get("content") for r in loop_rows
    ]
    assert len(channel.events) == 2
    assert channel.events[0].kind == DownlinkKind.BOOTSTRAP_INTERIM
    assert channel.events[1].kind == DownlinkKind.USER_REPLY
    assert any(
        d.kind == LoopDeliverableKind.USER_REPLY for d in loop_out.deliverables
    )
    assert MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP
    assert CompanionTurnTrack.USER_CHAT_BOOTSTRAP
    assert SOURCE_BOOTSTRAP_TRACK
