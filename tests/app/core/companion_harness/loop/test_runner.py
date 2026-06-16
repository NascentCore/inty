"""Trace-replay per-call streaming: interim deliver before next LLM call."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.parity.trace_replay import (
    completions_from_trace,
    interim_visible_text,
    llm_runs_for_in_turn_replay,
    load_trace_fixture,
    TraceReplayLLMClient,
)
from app.core.companion_harness.loop.runner import run_agentic_loop
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.services.agentic_companion.downlink import DownlinkKind
from app.utils.models_catalog import GenAIModel
from tests.app.core.companion_harness.loop.test_per_call_streaming import (
    _PerCallRecordingChannel,
)
from tests.app.core.companion_harness.loop.test_support import (
    build_agentic_loop_input,
)


class _ObservingTraceReplayLLMClient:
    """Assert interim channel events before each subsequent LLM call."""

    def __init__(
        self,
        inner: TraceReplayLLMClient,
        channel: _PerCallRecordingChannel,
    ) -> None:
        self._inner = inner
        self._channel = channel
        self._call_index = 0
        self.config = inner.config
        self.tools_per_call = inner.tools_per_call

    def resolve_model(self, role: str) -> GenAIModel:
        return self._inner.resolve_model(role)

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        if self._call_index >= 1:
            assert len(self._channel.events) == self._call_index
            assert (
                self._channel.events[self._call_index - 1].kind
                is DownlinkKind.USER_REPLY
            )
        result = self._inner.chat_completion(**kwargs)
        if self._call_index == 0:
            assert len(self._channel.events) == 0
        self._call_index += 1
        return result


def _last_user_content(messages: tuple[dict[str, Any], ...]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content")
            assert isinstance(content, str)
            return content
    raise AssertionError("no user message in trace inputs")


@pytest.mark.asyncio
async def test_trace_replay_interim_delivered_before_next_llm_call(
    tmp_path: Path,
) -> None:
    trace = load_trace_fixture()
    llm_runs = llm_runs_for_in_turn_replay(trace)
    first_inputs = llm_runs[0]["inputs"]
    assert isinstance(first_inputs, dict)
    openai_messages = tuple(first_inputs["messages"])
    openai_tools = tuple(first_inputs["tools"])
    completions = completions_from_trace(trace)

    scope = CompanionScope("trace-replay-interim", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    store.write_document("ai_private.jsonl", "")

    channel = _PerCallRecordingChannel()
    inner = TraceReplayLLMClient(completions)
    client = _ObservingTraceReplayLLMClient(inner, channel)

    loop_input = build_agentic_loop_input(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        openai_messages=openai_messages,
        openai_tools=openai_tools,
        user_text=_last_user_content(openai_messages),
        user_msg_uuid="trace-replay-user",
        trace_id="trace-replay",
        max_tool_rounds=8,
    )

    result = await run_agentic_loop(
        loop_input,
        llm_loop_mode=UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
        channel=channel,
    )
    channel.mark_runner_done()

    terminal_text = completions[2].choices[0].message.content.strip()
    interim_one = interim_visible_text(completions[0])
    interim_two = interim_visible_text(completions[1])

    assert channel.deliver_before_return is True
    assert len(channel.events) == 3
    assert channel.events[0].kind is DownlinkKind.USER_REPLY
    assert channel.events[0].assistant_text == interim_one
    assert channel.events[1].kind is DownlinkKind.USER_REPLY
    assert channel.events[1].assistant_text == interim_two
    assert channel.events[2].kind is DownlinkKind.USER_REPLY
    assert channel.events[2].assistant_text == terminal_text
    assert result.assistant_text == terminal_text
    assert len(result.deliverables) == 3

    ai_private = store.read_document("ai_private.jsonl")
    assert ai_private is not None
    ai_private_lines = [
        line for line in ai_private.splitlines() if line.strip()
    ]
    assert len(ai_private_lines) == 2
