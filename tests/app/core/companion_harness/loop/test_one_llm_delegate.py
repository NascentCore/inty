"""Tests for ``OneModelInTurnSyncMechanism`` delegate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.loop.channel_adapter import RecordingChannelAdapter
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.runner import run_agentic_loop
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.services.agentic_companion.downlink import DownlinkKind
from tests.app.core.companion_harness.companion.test_in_turn_sync_tool_loop import (
    _FakeSyncToolLoopLLMClient,
    _final_response,
    _tool_response,
)
from tests.app.core.companion_harness.loop.test_support import (
    build_agentic_loop_input,
)


@pytest.mark.asyncio
async def test_one_llm_delegate_matches_sync_tool_loop_terminal(tmp_path: Path) -> None:
    scope = CompanionScope("loop-one-llm", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    client = _FakeSyncToolLoopLLMClient([_final_response(content="done")])
    channel = RecordingChannelAdapter()
    loop_input = build_agentic_loop_input(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        openai_messages=({"role": "user", "content": "hi"},),
        openai_tools=(),
        user_text="hi",
        user_msg_uuid="user-1",
        trace_id="trace-1",
    )
    result = await run_agentic_loop(
        loop_input,
        llm_loop_mode=UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
        channel=channel,
    )
    assert result.assistant_text == "done"
    assert result.tool_background_started is False
    assert len(channel.events) == 1
    assert channel.events[0].kind == DownlinkKind.USER_REPLY


@pytest.mark.asyncio
async def test_one_llm_delegate_per_call_interim_and_terminal(tmp_path: Path) -> None:
    scope = CompanionScope("loop-one-llm-interim", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    store.write_document("IDENTITY.md", "IDENTITY\n")
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
    channel = RecordingChannelAdapter()
    loop_input = build_agentic_loop_input(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        openai_messages=({"role": "user", "content": "go"},),
        openai_tools=(
            {
                "type": "function",
                "function": {
                    "name": "memory_store_write_document",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ),
        user_text="go",
        user_msg_uuid="user-2",
        trace_id="trace-2",
    )
    result = await run_agentic_loop(
        loop_input,
        llm_loop_mode=UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
        channel=channel,
    )
    assert result.assistant_text == "terminal line"
    assert len(channel.events) == 2
    assert channel.events[0].kind == DownlinkKind.BOOTSTRAP_INTERIM
    assert channel.events[0].assistant_text == "interim line"
    assert channel.events[1].kind == DownlinkKind.USER_REPLY
    assert channel.events[1].assistant_text == "terminal line"
