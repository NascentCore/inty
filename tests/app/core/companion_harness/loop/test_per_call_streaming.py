"""per-call-streaming: channel deliver before ``run_agentic_loop`` returns."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.loop.channel_adapter import RecordingChannelAdapter
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.parity.fixtures import (
    FakeDualLlmClient,
    FakeSyncToolLoopLLMClient,
    dual_llm_fg_response,
    dual_llm_tool_finish_response,
    final_response,
    tool_response,
)
from app.core.companion_harness.loop.runner import run_agentic_loop
from app.core.companion_harness.memory.memory_store import MemoryStore
from tests.app.core.companion_harness.loop.test_support import (
    build_agentic_loop_input,
)


class _PerCallRecordingChannel(RecordingChannelAdapter):
    """Records whether deliver ran before runner return."""

    def __init__(self) -> None:
        super().__init__()
        self.deliver_before_return = False
        self._runner_done = False

    async def deliver(self, event: object) -> None:
        if not self._runner_done:
            self.deliver_before_return = True
        await super().deliver(event)  # type: ignore[arg-type]

    def mark_runner_done(self) -> None:
        self._runner_done = True


@pytest.mark.asyncio
async def test_per_call_streaming_one_llm_deliver_before_return(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("loop-per-call-1", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    store.write_document("IDENTITY.md", "IDENTITY\n")
    client = FakeSyncToolLoopLLMClient(
        [
            tool_response(
                content="interim",
                tool_name="memory_store_write_document",
                tool_arguments=json.dumps(
                    {"relative_path": "IDENTITY.md", "content": "x\n"},
                    ensure_ascii=False,
                ),
            ),
            final_response(content="terminal"),
        ]
    )
    channel = _PerCallRecordingChannel()
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
        user_msg_uuid="user-pcs",
        trace_id="trace-pcs",
    )
    result = await run_agentic_loop(
        loop_input,
        llm_loop_mode=UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
        channel=channel,
    )
    channel.mark_runner_done()
    assert channel.deliver_before_return is True
    assert len(channel.events) == 2
    assert result.assistant_text == "terminal"


@pytest.mark.asyncio
async def test_per_call_streaming_two_llm_deliver_before_return(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("loop-per-call-2", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")

    def _tool_sync(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return dual_llm_tool_finish_response()

    client = FakeDualLlmClient(
        fg_response=dual_llm_fg_response(text="fg per-call"),
        tool_sync_handler=_tool_sync,
    )
    channel = _PerCallRecordingChannel()
    msgs = ({"role": "user", "content": "hi"},)
    loop_input = build_agentic_loop_input(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        openai_messages=msgs,
        openai_tools=(),
        user_text="hi",
        user_msg_uuid="user-pcs-2",
        trace_id="trace-pcs-2",
        skip_foreground_envelope=False,
        dual_llm_chat_msgs=msgs,
        dual_llm_tool_msgs=msgs,
    )
    result = await run_agentic_loop(
        loop_input,
        llm_loop_mode=UserTurnLlmLoopMode.DUAL_LLM,
        channel=channel,
    )
    channel.mark_runner_done()
    assert channel.deliver_before_return is True
    assert len(channel.events) >= 1
    assert result.assistant_text == "fg per-call"
