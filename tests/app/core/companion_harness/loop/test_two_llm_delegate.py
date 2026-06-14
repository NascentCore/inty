"""Tests for ``TwoModelChatThenToolBgMechanism`` delegate."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.loop.channel_adapter import RecordingChannelAdapter
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.parity.fixtures import (
    FakeDualLlmClient,
    dual_llm_fg_response,
    dual_llm_tool_finish_response,
)
from app.core.companion_harness.loop.runner import run_agentic_loop
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.services.agentic_companion.downlink import DownlinkKind
from tests.app.core.companion_harness.loop.test_support import (
    build_agentic_loop_input,
)


@pytest.mark.asyncio
async def test_two_llm_skip_foreground_envelope(tmp_path: Path) -> None:
    scope = CompanionScope("loop-two-llm-skip", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")

    def _tool_sync(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return dual_llm_tool_finish_response()

    client = FakeDualLlmClient(
        fg_response=dual_llm_fg_response(text="unused"),
        tool_sync_handler=_tool_sync,
    )
    channel = RecordingChannelAdapter()
    msgs = ({"role": "user", "content": "maint"},)
    loop_input = build_agentic_loop_input(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        openai_messages=msgs,
        openai_tools=(),
        user_text="maint",
        user_msg_uuid="user-maint",
        trace_id="trace-maint",
        skip_foreground_envelope=True,
        dual_llm_chat_msgs=msgs,
        dual_llm_tool_msgs=msgs,
    )
    result = await run_agentic_loop(
        loop_input,
        llm_loop_mode=UserTurnLlmLoopMode.DUAL_LLM,
        channel=channel,
    )
    assert result.assistant_text == ""
    assert result.tool_background_started is True
    assert client.fg_called is False


@pytest.mark.asyncio
async def test_two_llm_foreground_per_call_deliver(tmp_path: Path) -> None:
    scope = CompanionScope("loop-two-llm-fg", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")

    def _tool_sync(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return dual_llm_tool_finish_response()

    client = FakeDualLlmClient(
        fg_response=dual_llm_fg_response(text="foreground ok"),
        tool_sync_handler=_tool_sync,
    )
    channel = RecordingChannelAdapter()
    msgs = ({"role": "user", "content": "hi"},)
    loop_input = build_agentic_loop_input(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        openai_messages=msgs,
        openai_tools=(),
        user_text="hi",
        user_msg_uuid="user-fg",
        trace_id="trace-fg",
        skip_foreground_envelope=False,
        dual_llm_chat_msgs=msgs,
        dual_llm_tool_msgs=msgs,
    )
    result = await run_agentic_loop(
        loop_input,
        llm_loop_mode=UserTurnLlmLoopMode.DUAL_LLM,
        channel=channel,
    )
    assert result.assistant_text == "foreground ok"
    assert result.tool_background_started is True
    assert len(channel.events) >= 1
    assert channel.events[0].kind == DownlinkKind.USER_REPLY
    assert channel.events[0].assistant_text == "foreground ok"
