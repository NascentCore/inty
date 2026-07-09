"""Unit tests for domain ``OutputQueue`` persist-before-ready semantics."""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.agentic_companion.output_queue import (
    OutputDeliveryAck,
    OutputDeliveryFailure,
    OutputDeliverySkip,
    OutputDeliveryUnroutableError,
    OutputQueue,
    OutputQueueAppendInput,
    ReadyOutputMessage,
    clear_output_queues_for_tests,
    get_output_queue_for_scope,
)
from app.core.agentic_companion.types import (
    AgentOutputMessage,
    OutputQueueRecord,
    QueueClaim,
    QueueStatus,
    WireId,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.agentic_companion.types import OutputMessageKind


class _FakePersistedOutputRecord:
    """Minimal ``append_agent_output`` return shape after OutputQueue wire-meta extension."""

    def __init__(self, message_id: str, text: str, sequence: int) -> None:
        self.message_id = message_id
        self.text = text
        self.sequence = sequence
        self.tool_background_started = False
        self.generated_images = ()
        self.trace_id = None
        self.langsmith_trace_id = None
        self.langsmith_run_id = None
        self.turn_recall = None


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    clear_output_queues_for_tests()
    yield
    clear_output_queues_for_tests()


def _append_input(
    *,
    batch_id: str,
    text: str,
    kind: OutputMessageKind = OutputMessageKind.USER_REPLY,
) -> OutputQueueAppendInput:
    return OutputQueueAppendInput(
        kind=kind,
        batch_id=batch_id,
        text=text,
        message_ids=("input-1",),
        trace_id="trace-1",
        langsmith_trace_id=None,
        langsmith_run_id=None,
        turn_recall=None,
    )


@pytest.mark.asyncio
async def test_append_failed_db_produces_no_ready_marker() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    queue = OutputQueue(scope=scope)
    with patch(
        "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository.append_agent_output",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db down"),
    ):
        with pytest.raises(RuntimeError, match="db down"):
            await queue.append_visible_message(
                _append_input(batch_id="batch-1", text="hello")
            )
    assert await queue.pull_ready_batch() == ()


@pytest.mark.asyncio
async def test_append_agent_initiated_uses_synthetic_batch_id() -> None:
    scope = AgentScope(user_id="u-agent", agent_id="a-agent")
    queue = OutputQueue(scope=scope)

    class _FakeRecord(_FakePersistedOutputRecord):
        pass

    with patch(
        "app.core.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        repo.append_agent_output = AsyncMock(
            return_value=_FakeRecord("msg-proactive", "hello", 1)
        )
        with patch(
            "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            ready = await queue.append_visible_message(
                OutputQueueAppendInput(
                    kind=OutputMessageKind.PROACTIVE,
                    batch_id="",
                    text="hello",
                    message_ids=(),
                    trace_id=None,
                    langsmith_trace_id=None,
                    langsmith_run_id=None,
                    turn_recall=None,
                )
            )

    assert ready.kind == OutputMessageKind.PROACTIVE
    assert ready.message_ids == ()
    assert ready.batch_id.startswith("agent-initiated:")
    persisted = repo.append_agent_output.await_args.args[0]
    assert persisted.kind == OutputMessageKind.PROACTIVE


@pytest.mark.asyncio
async def test_ready_message_carries_trace_fields_from_append_input() -> None:
    scope = AgentScope(user_id="u-trace", agent_id="a-trace")
    queue = OutputQueue(scope=scope)

    class _FakeRecord(_FakePersistedOutputRecord):
        pass

    fake_record = _FakeRecord("msg-trace", "hello", 1)
    fake_record.trace_id = "trace-abc"
    fake_record.langsmith_trace_id = "ls-trace"
    fake_record.langsmith_run_id = "ls-run"

    with patch(
        "app.core.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        repo.append_agent_output = AsyncMock(return_value=fake_record)
        with patch(
            "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            ready = await queue.append_visible_message(
                OutputQueueAppendInput(
                    kind=OutputMessageKind.USER_REPLY,
                    batch_id="batch-trace",
                    text="hello",
                    message_ids=("input-trace",),
                    trace_id="trace-abc",
                    langsmith_trace_id="ls-trace",
                    langsmith_run_id="ls-run",
                    turn_recall=None,
                )
            )

    assert ready.trace_id == "trace-abc"
    assert ready.langsmith_trace_id == "ls-trace"
    assert ready.langsmith_run_id == "ls-run"


@pytest.mark.asyncio
async def test_ready_message_from_record_maps_trace_fields() -> None:
    scope = AgentScope(user_id="u-rec", agent_id="a-rec")
    queue = OutputQueue(scope=scope)
    record = OutputQueueRecord(
        message_id="msg-rec",
        scope=scope,
        sequence=3,
        status=QueueStatus.PENDING,
        batch_id="batch-rec",
        kind=OutputMessageKind.USER_REPLY,
        text="recovered",
        created_at_utc=datetime.now(UTC),
        message_ids=("input-rec",),
        trace_id="trace-rec",
        langsmith_trace_id="ls-rec",
        langsmith_run_id="run-rec",
    )
    ready = queue._ready_message_from_record(record)
    assert ready.trace_id == "trace-rec"
    assert ready.langsmith_trace_id == "ls-rec"
    assert ready.langsmith_run_id == "run-rec"


@pytest.mark.asyncio
async def test_multiple_appends_pulled_in_order() -> None:
    scope = AgentScope(user_id="u2", agent_id="a2")
    queue = OutputQueue(scope=scope)

    class _FakeRecord(_FakePersistedOutputRecord):
        pass

    with patch(
        "app.core.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        repo.append_agent_output = AsyncMock(
            side_effect=[
                _FakeRecord("msg-a", "first", 1),
                _FakeRecord("msg-b", "second", 2),
            ]
        )
        with patch(
            "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            await queue.append_visible_message(
                _append_input(batch_id="batch-1", text="first")
            )
            await queue.append_visible_message(
                _append_input(batch_id="batch-1", text="second")
            )

    batch = await queue.pull_ready_batch()
    assert tuple(m.message_id for m in batch) == ("msg-a", "msg-b")
    assert await queue.pull_ready_batch() == ()


@pytest.mark.asyncio
async def test_ack_delivered_and_mark_failed_call_repository() -> None:
    scope = AgentScope(user_id="u3", agent_id="a3")
    queue = OutputQueue(scope=scope)
    delivered_at = datetime.now(UTC)
    with patch(
        "app.core.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        with patch(
            "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            await queue.ack_delivered(
                OutputDeliveryAck(
                    message_id="msg-1",
                    delivered_at_utc=delivered_at,
                )
            )
            await queue.mark_delivery_failed(
                OutputDeliveryFailure(
                    message_id="msg-2",
                    error_message="transport broken",
                )
            )
    repo.mark_delivered.assert_awaited_once()
    repo.mark_failed.assert_awaited_once_with(
        "msg-2",
        error_message="transport broken",
    )


@pytest.mark.asyncio
async def test_mark_failed_waits_for_repository_retry() -> None:
    scope = AgentScope(user_id="u4", agent_id="a4")
    queue = OutputQueue(scope=scope)
    ready = ReadyOutputMessage(
        message_id="msg-retry",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="retry me",
        sequence=1,
        message_ids=("input-1",),
    )
    queue._ready.append(ready)
    assert await queue.pull_ready_batch() == (ready,)
    with patch(
        "app.core.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        with patch(
            "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            await queue.mark_delivery_failed(
                OutputDeliveryFailure(
                    message_id=ready.message_id,
                    error_message="transport broken",
                )
            )
    assert await queue.pull_ready_batch() == ()


@pytest.mark.asyncio
async def test_skip_delivery_calls_mark_skipped_without_requeue() -> None:
    scope = AgentScope(user_id="u-skip", agent_id="a-skip")
    queue = OutputQueue(scope=scope)
    ready = ReadyOutputMessage(
        message_id="msg-skip",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="skip me",
        sequence=1,
        message_ids=("input-1",),
    )
    queue._ready.append(ready)
    assert await queue.pull_ready_batch() == (ready,)
    with patch(
        "app.core.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        with patch(
            "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            await queue.skip_delivery(
                OutputDeliverySkip(
                    message_id=ready.message_id,
                    error_message="no delivery hook",
                )
            )
    repo.mark_skipped.assert_awaited_once_with(
        ready.message_id,
        error_message="no delivery hook",
    )
    assert await queue.pull_ready_batch() == ()


@pytest.mark.asyncio
async def test_pull_ready_batch_claims_persisted_pending_after_memory_loss() -> (
    None
):
    scope = AgentScope(user_id="u-recover", agent_id="a-recover")
    queue = OutputQueue(scope=scope)
    record = OutputQueueRecord(
        message_id="msg-recovered",
        scope=scope,
        sequence=7,
        status=QueueStatus.CLAIMED,
        batch_id="agent-initiated:recover",
        kind=OutputMessageKind.PROACTIVE,
        text="recovered line",
        created_at_utc=datetime.now(UTC),
        message_ids=(),
    )
    claim = QueueClaim(
        record=record,
        delivery_channel=ChannelKind.TELEGRAM,
        delivery_wire_id=WireId(value="telegram:u-recover:a-recover"),
    )

    with patch(
        "app.core.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        repo.claim_pending_for_delivery = AsyncMock(return_value=(claim,))
        with patch(
            "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            batch = await queue.pull_ready_batch(
                delivery_channel=ChannelKind.TELEGRAM,
                delivery_wire_id="telegram:u-recover:a-recover",
            )

    assert tuple(message.message_id for message in batch) == ("msg-recovered",)
    repo.claim_pending_for_delivery.assert_awaited_once_with(
        scope,
        delivery_channel=ChannelKind.TELEGRAM,
        delivery_wire_id="telegram:u-recover:a-recover",
        limit=100,
    )
    session.commit.assert_awaited_once()


def test_output_delivery_unroutable_error_carries_scope_and_message_ids() -> (
    None
):
    scope = AgentScope(user_id="u-err", agent_id="a-err")
    message_ids = ("queue-msg-1",)
    error = OutputDeliveryUnroutableError(scope, message_ids)
    assert error.scope is scope
    assert error.message_ids == message_ids
    assert "queue-msg-1" in str(error)


@pytest.mark.asyncio
async def test_append_during_pull_ready_batch_is_not_lost() -> None:
    """``pull_ready_batch`` holds ``_memory_lock`` until clear completes."""
    scope = AgentScope(user_id="u7", agent_id="a7")
    queue = OutputQueue(scope=scope)
    msg_a = ReadyOutputMessage(
        message_id="msg-a",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="first",
        sequence=1,
        message_ids=("input-1",),
    )
    msg_b = ReadyOutputMessage(
        message_id="msg-b",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="second",
        sequence=2,
        message_ids=("input-1",),
    )
    queue._ready.append(msg_a)
    pull_started = asyncio.Event()

    async def pull() -> tuple[ReadyOutputMessage, ...]:
        pull_started.set()
        return await queue.pull_ready_batch()

    async def append_after_pull_starts() -> None:
        await pull_started.wait()
        async with queue._memory_lock:
            queue._ready.append(msg_b)

    pull_task = asyncio.create_task(pull())
    append_task = asyncio.create_task(append_after_pull_starts())
    first_batch = await pull_task
    await append_task
    assert first_batch == (msg_a,)
    assert await queue.pull_ready_batch() == (msg_b,)


@pytest.mark.asyncio
async def test_concurrent_append_and_pull_deliver_every_message() -> None:
    scope = AgentScope(user_id="u8", agent_id="a8")
    queue = OutputQueue(scope=scope)
    message_count = 64
    pulled_ids: set[str] = set()
    pulled_lock = asyncio.Lock()
    delivered_at = datetime.now(UTC)

    class _FakeRecord(_FakePersistedOutputRecord):
        pass

    sequence = 0

    def _next_record(_: AgentOutputMessage) -> _FakeRecord:
        nonlocal sequence
        sequence += 1
        message_id = f"msg-{sequence}"
        return _FakeRecord(message_id, f"text-{sequence}", sequence)

    async def pump_until_done(done: asyncio.Event) -> None:
        while not done.is_set() or queue._ready:
            batch = await queue.pull_ready_batch()
            for message in batch:
                async with pulled_lock:
                    pulled_ids.add(message.message_id)
                await queue.ack_delivered(
                    OutputDeliveryAck(
                        message_id=message.message_id,
                        delivered_at_utc=delivered_at,
                    )
                )
            await asyncio.sleep(0)

    with patch(
        "app.core.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        repo.append_agent_output = AsyncMock(side_effect=_next_record)
        repo.mark_delivered = AsyncMock()
        with patch(
            "app.core.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            done = asyncio.Event()
            pump_task = asyncio.create_task(pump_until_done(done))
            for index in range(message_count):
                await queue.append_visible_message(
                    _append_input(
                        batch_id=f"batch-{index}",
                        text=f"hello-{index}",
                    )
                )
                if index % 4 == 0:
                    await asyncio.sleep(0)
            done.set()
            await pump_task

    assert len(pulled_ids) == message_count
    assert pulled_ids == {
        f"msg-{index}" for index in range(1, message_count + 1)
    }


def test_registry_returns_one_instance_per_scope() -> None:
    scope = AgentScope(user_id="u5", agent_id="a5")
    first = get_output_queue_for_scope(scope)
    second = get_output_queue_for_scope(scope)
    assert first is second


def test_registry_returns_one_instance_under_concurrent_creation() -> None:
    scope = AgentScope(user_id="u6", agent_id="a6")

    def _build_queue(scope: AgentScope) -> OutputQueue:
        time.sleep(0.05)
        return OutputQueue(scope=scope)

    with patch(
        "app.core.agentic_companion.output_queue.OutputQueue",
        side_effect=_build_queue,
    ):
        results: list[OutputQueue] = []
        threads = [
            threading.Thread(
                target=lambda: results.append(get_output_queue_for_scope(scope))
            )
            for _ in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=1)

    assert len(results) == 2
    assert results[0] is results[1]
