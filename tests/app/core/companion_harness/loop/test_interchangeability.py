"""Interchangeability: same input, swap ``llm_loop_mode``, stable interface."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.loop.channel_adapter import RecordingChannelAdapter
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.contract import AgenticLoopOutput
from app.core.companion_harness.loop.output_queue import LoopDeliverableKind
from app.core.companion_harness.loop.runner import run_agentic_loop
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.loop.parity.fixtures import (
    FakeDualLlmClient,
    dual_llm_fg_response,
    dual_llm_tool_finish_response,
)
from tests.app.core.companion_harness.companion.test_in_turn_sync_tool_loop import (
    _FakeSyncToolLoopLLMClient,
    _final_response,
)
from tests.app.core.companion_harness.loop.test_support import (
    build_agentic_loop_input,
)


@pytest.mark.asyncio
async def test_interchangeability_same_input_swap_mode(tmp_path: Path) -> None:
    scope = CompanionScope("loop-interchange", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    msgs = ({"role": "user", "content": "hi"},)

    one_client = _FakeSyncToolLoopLLMClient([_final_response(content="one-llm")])
    one_input = build_agentic_loop_input(
        store=store,
        llm_client=one_client,  # type: ignore[arg-type]
        openai_messages=msgs,
        openai_tools=(),
        user_text="hi",
        user_msg_uuid="user-x",
        trace_id="trace-x",
        dual_llm_chat_msgs=msgs,
        dual_llm_tool_msgs=msgs,
    )

    def _tool_sync(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return dual_llm_tool_finish_response()

    two_client = FakeDualLlmClient(
        fg_response=dual_llm_fg_response(text="two-llm"),
        tool_sync_handler=_tool_sync,
    )
    two_input = build_agentic_loop_input(
        store=store,
        llm_client=two_client,  # type: ignore[arg-type]
        openai_messages=msgs,
        openai_tools=(),
        user_text="hi",
        user_msg_uuid="user-x",
        trace_id="trace-x",
        skip_foreground_envelope=False,
        dual_llm_chat_msgs=msgs,
        dual_llm_tool_msgs=msgs,
    )

    channel_a = RecordingChannelAdapter()
    out_a = await run_agentic_loop(
        one_input,
        llm_loop_mode=UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
        channel=channel_a,
    )
    channel_b = RecordingChannelAdapter()
    out_b = await run_agentic_loop(
        two_input,
        llm_loop_mode=UserTurnLlmLoopMode.DUAL_LLM,
        channel=channel_b,
    )

    assert isinstance(out_a, AgenticLoopOutput)
    assert isinstance(out_b, AgenticLoopOutput)
    assert out_a.tool_background_started is False
    assert out_b.tool_background_started is True
    assert out_a.assistant_text == "one-llm"
    assert out_b.assistant_text == "two-llm"
    for deliverable in out_a.deliverables:
        assert deliverable.kind in LoopDeliverableKind
    for deliverable in out_b.deliverables:
        assert deliverable.kind in LoopDeliverableKind
