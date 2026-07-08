"""Unit tests for IM eval trace projection into chat_history (#3663)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
)
from app.core.companion_harness.agentic_companion.types import (
    InputQueueRecord,
    QueueStatus,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.companion_harness.agentic_companion.types import OutputMessageKind
from app.services.agentic_companion import eval_trace_projector as projector_mod
from app.services.agentic_companion.eval_trace_projector import (
    EvalTraceAssistantInput,
    EvalTraceInboundInput,
    project_assistant_delivery,
    project_inbound_user,
    should_project_channel,
)


# TODO(#3663): share FakeChatHistoryRecorder with test_eval_trace_im_integration.py.
@dataclass
class FakeChatHistoryRecorder:
    """Records chat_history writes for eval trace projector tests."""

    user_calls: list[tuple[str, str, dict[str, object] | None]] = field(
        default_factory=list
    )
    ai_calls: list[tuple[str, str, str | None, dict[str, object] | None]] = (
        field(default_factory=list)
    )
    next_user_id: int = 100
    next_ai_id: int = 200

    async def add_user_message_async(
        self,
        session_id: str,
        message: str,
        meta_data: dict[str, object] | None = None,
    ) -> int | None:
        self.user_calls.append((session_id, message, meta_data))
        row_id = self.next_user_id
        self.next_user_id += 1
        return row_id

    async def add_ai_message_sync_async(
        self,
        session_id: str,
        message: str,
        agent_id: str | None = None,
        meta_data: dict[str, object] | None = None,
    ) -> int | None:
        self.ai_calls.append((session_id, message, agent_id, meta_data))
        row_id = self.next_ai_id
        self.next_ai_id += 1
        return row_id


@pytest.fixture
def fake_history(monkeypatch: pytest.MonkeyPatch) -> FakeChatHistoryRecorder:
    recorder = FakeChatHistoryRecorder()
    monkeypatch.setattr(projector_mod, "chat_history_service", recorder)
    return recorder


def test_should_project_channel_im_only() -> None:
    assert should_project_channel(ChannelKind.TELEGRAM)
    assert should_project_channel(ChannelKind.WECHAT_WEIXIN)
    assert not should_project_channel(ChannelKind.APP_WS)
    assert not should_project_channel(ChannelKind.SMS)


@pytest.mark.asyncio
async def test_project_inbound_user_telegram_writes_meta(
    fake_history: FakeChatHistoryRecorder,
) -> None:
    scope = AgentScope(user_id="user-tg", agent_id="agent-tg")
    row_id = await project_inbound_user(
        EvalTraceInboundInput(
            scope=scope,
            runtime_channel=ChannelKind.TELEGRAM,
            user_text="hello from telegram",
            queue_message_id="queue-msg-1",
        )
    )
    assert row_id == 100
    assert len(fake_history.user_calls) == 1
    session_id, text, meta = fake_history.user_calls[0]
    assert text == "hello from telegram"
    assert meta is not None
    assert meta["runtimeChannel"] == ChannelKind.TELEGRAM.value
    assert meta["user_msg_uuid"] == "queue-msg-1"


@pytest.mark.asyncio
async def test_project_inbound_user_app_ws_no_op(
    fake_history: FakeChatHistoryRecorder,
) -> None:
    scope = AgentScope(user_id="user-ws", agent_id="agent-ws")
    row_id = await project_inbound_user(
        EvalTraceInboundInput(
            scope=scope,
            runtime_channel=ChannelKind.APP_WS,
            user_text="hello",
            queue_message_id="queue-msg-ws",
        )
    )
    assert row_id is None
    assert fake_history.user_calls == []


@pytest.mark.asyncio
async def test_project_assistant_delivery_carries_trace_fields(
    fake_history: FakeChatHistoryRecorder,
) -> None:
    scope = AgentScope(user_id="user-ai", agent_id="agent-ai")
    primary = InputQueueRecord(
        message_id="input-1",
        scope=scope,
        sequence=0,
        status=QueueStatus.CLAIMED,
        channel=ChannelKind.TELEGRAM,
        wire_id="telegram:wire",
        text="hi",
        received_at_utc=datetime.now(UTC),
    )
    ready = ReadyOutputMessage(
        message_id="out-1",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="reply text",
        sequence=1,
        message_ids=("input-1",),
        trace_id="trace-xyz",
        langsmith_trace_id="ls-xyz",
        langsmith_run_id="run-xyz",
    )
    await project_assistant_delivery(
        EvalTraceAssistantInput(
            scope=scope,
            runtime_channel=ChannelKind.TELEGRAM,
            ready_message=ready,
            primary_input=primary,
        )
    )
    assert len(fake_history.ai_calls) == 1
    session_id, text, agent_id, meta = fake_history.ai_calls[0]
    assert text == "reply text"
    assert agent_id == "agent-ai"
    assert meta is not None
    assert meta["runtimeChannel"] == ChannelKind.TELEGRAM.value
    assert meta["trace_id"] == "trace-xyz"
    assert meta["langsmith_trace_id"] == "ls-xyz"
    assert meta["langsmith_run_id"] == "run-xyz"
    assert meta["user_msg_uuid"] == "input-1"
    assert meta["assistant_msg_uuid"] == "out-1"


@pytest.mark.asyncio
async def test_project_assistant_delivery_skips_app_ws(
    fake_history: FakeChatHistoryRecorder,
) -> None:
    scope = AgentScope(user_id="user-skip", agent_id="agent-skip")
    ready = ReadyOutputMessage(
        message_id="out-skip",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="reply",
        sequence=1,
        message_ids=("input-skip",),
    )
    await project_assistant_delivery(
        EvalTraceAssistantInput(
            scope=scope,
            runtime_channel=ChannelKind.APP_WS,
            ready_message=ready,
            primary_input=None,
        )
    )
    assert fake_history.ai_calls == []
