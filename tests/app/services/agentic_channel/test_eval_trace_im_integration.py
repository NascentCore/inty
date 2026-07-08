"""Integration tests for IM eval trace hooks in serving and presence (#3663)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
    clear_output_queues_for_tests,
    get_output_queue_for_scope,
)
from app.core.companion_harness.agentic_companion.types import (
    InputQueueRecord,
    OutputMessageKind,
    QueueStatus,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.services.agentic_channel import serving as serving_mod
from app.services.agentic_channel.serving import _deliver_ready_message
from app.services.agentic_companion import eval_trace_projector as projector_mod
from app.services.chat_service import generate_session_id


# TODO(#3663): share FakeChatHistoryRecorder with test_eval_trace_projector.py.
@dataclass
class FakeChatHistoryRecorder:
    user_calls: list[tuple[str, str, dict[str, object] | None]] = field(
        default_factory=list
    )
    ai_calls: list[tuple[str, str, str | None, dict[str, object] | None]] = (
        field(default_factory=list)
    )
    next_user_id: int = 501
    next_ai_id: int = 601

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


class FakeInputQueueRepository:
    def __init__(self, records: tuple[InputQueueRecord, ...]) -> None:
        self._records = records

    async def get_records_by_ids(
        self,
        scope: AgentScope,
        message_ids: tuple[str, ...],
    ) -> tuple[InputQueueRecord, ...]:
        assert scope is not None
        return tuple(
            record
            for record in self._records
            if record.message_id in message_ids
        )


@pytest.fixture(autouse=True)
def _clear_output_queue_registry() -> None:
    clear_output_queues_for_tests()
    yield
    clear_output_queues_for_tests()


@pytest.fixture
def fake_history(monkeypatch: pytest.MonkeyPatch) -> FakeChatHistoryRecorder:
    recorder = FakeChatHistoryRecorder()
    monkeypatch.setattr(projector_mod, "chat_history_service", recorder)
    return recorder


@pytest.mark.asyncio
async def test_deliver_ready_message_projects_telegram_assistant_row(
    fake_history: FakeChatHistoryRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = AgentScope(user_id="user-im", agent_id="agent-im")
    session_id = generate_session_id(scope.memory_store_chat_id())
    primary = InputQueueRecord(
        message_id="in-im-1",
        scope=scope,
        sequence=0,
        status=QueueStatus.CLAIMED,
        channel=ChannelKind.TELEGRAM,
        wire_id="telegram:wire",
        text="hello",
        received_at_utc=datetime.now(UTC),
        chat_history_user_row_id=501,
    )
    ready = ReadyOutputMessage(
        message_id="out-im-1",
        batch_id="batch-im",
        kind=OutputMessageKind.USER_REPLY,
        text="assistant reply",
        sequence=1,
        message_ids=("in-im-1",),
        trace_id="trace-im",
        langsmith_trace_id="ls-im",
    )
    queue = get_output_queue_for_scope(scope)
    queue._ready.append(ready)
    assert await queue.pull_ready_batch() == (ready,)

    async def deliver_message(_message: ReadyOutputMessage) -> None:
        return None

    monkeypatch.setattr(
        serving_mod,
        "PostgresInputQueueRepository",
        lambda _db: FakeInputQueueRepository((primary,)),
    )
    monkeypatch.setattr(
        serving_mod,
        "AsyncSessionLocal",
        _fake_session_local,
    )

    delivered = await _deliver_ready_message(
        message=ready,
        deliver_message=deliver_message,
        scope=scope,
        delivery_channel=ChannelKind.TELEGRAM,
    )
    assert delivered == "assistant reply"
    assert len(fake_history.ai_calls) == 1
    ai_session_id, ai_text, agent_id, meta = fake_history.ai_calls[0]
    assert ai_session_id == session_id
    assert ai_text == "assistant reply"
    assert agent_id == "agent-im"
    assert meta is not None
    assert meta["runtimeChannel"] == ChannelKind.TELEGRAM.value
    assert meta["trace_id"] == "trace-im"
    assert meta["langsmith_trace_id"] == "ls-im"
    assert meta["user_msg_uuid"] == "in-im-1"


class _FakeDbSession:
    async def __aenter__(self) -> _FakeDbSession:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


def _fake_session_local() -> _FakeDbSession:
    return _FakeDbSession()


@pytest.mark.asyncio
async def test_deliver_ready_message_skips_projection_for_app_ws(
    fake_history: FakeChatHistoryRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = AgentScope(user_id="user-ws-skip", agent_id="agent-ws-skip")
    ready = ReadyOutputMessage(
        message_id="out-ws",
        batch_id="batch-ws",
        kind=OutputMessageKind.USER_REPLY,
        text="ws reply",
        sequence=1,
        message_ids=("in-ws",),
    )
    queue = get_output_queue_for_scope(scope)
    queue._ready.append(ready)
    assert await queue.pull_ready_batch() == (ready,)

    primary = InputQueueRecord(
        message_id="in-ws",
        scope=scope,
        sequence=0,
        status=QueueStatus.CLAIMED,
        channel=ChannelKind.APP_WS,
        wire_id="app:wire",
        text="hi",
        received_at_utc=datetime.now(UTC),
    )
    monkeypatch.setattr(
        serving_mod,
        "PostgresInputQueueRepository",
        lambda _db: FakeInputQueueRepository((primary,)),
    )
    monkeypatch.setattr(
        serving_mod,
        "AsyncSessionLocal",
        _fake_session_local,
    )

    async def deliver_message(_message: ReadyOutputMessage) -> None:
        return None

    await _deliver_ready_message(
        message=ready,
        deliver_message=deliver_message,
        scope=scope,
        delivery_channel=ChannelKind.APP_WS,
    )
    assert fake_history.ai_calls == []


@pytest.mark.asyncio
async def test_deliver_ready_message_acks_when_projection_fails(
    fake_history: FakeChatHistoryRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = AgentScope(user_id="user-proj-fail", agent_id="agent-proj-fail")
    ready = ReadyOutputMessage(
        message_id="out-fail",
        batch_id="batch-fail",
        kind=OutputMessageKind.USER_REPLY,
        text="reply despite projection failure",
        sequence=1,
        message_ids=("in-fail",),
    )
    queue = get_output_queue_for_scope(scope)
    queue._ready.append(ready)
    assert await queue.pull_ready_batch() == (ready,)

    primary = InputQueueRecord(
        message_id="in-fail",
        scope=scope,
        sequence=0,
        status=QueueStatus.CLAIMED,
        channel=ChannelKind.TELEGRAM,
        wire_id="telegram:wire",
        text="hi",
        received_at_utc=datetime.now(UTC),
    )
    monkeypatch.setattr(
        serving_mod,
        "PostgresInputQueueRepository",
        lambda _db: FakeInputQueueRepository((primary,)),
    )
    monkeypatch.setattr(
        serving_mod,
        "AsyncSessionLocal",
        _fake_session_local,
    )

    async def deliver_message(_message: ReadyOutputMessage) -> None:
        return None

    async def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("projection unavailable")

    monkeypatch.setattr(
        serving_mod,
        "project_assistant_delivery",
        boom,
    )
    ack_mock = AsyncMock()
    monkeypatch.setattr(
        queue,
        "ack_delivered",
        ack_mock,
    )

    delivered = await _deliver_ready_message(
        message=ready,
        deliver_message=deliver_message,
        scope=scope,
        delivery_channel=ChannelKind.TELEGRAM,
    )
    assert delivered == "reply despite projection failure"
    assert fake_history.ai_calls == []
    ack_mock.assert_awaited_once()
