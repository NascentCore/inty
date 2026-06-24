"""Tests for user-chat drain + OutputQueue pull delivery glue."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from itertools import chain, repeat
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
    clear_output_queues_for_tests,
    get_output_queue_for_scope,
)
from app.core.companion_harness.agentic_companion.types import (
    OutputQueueRecord,
    QueueClaim,
    QueueStatus,
    WireId,
)
from app.services.agentic_channel.serving import (
    DrainScopeOnceResult,
    UserChatTurnDeliveryResult,
    _deliver_ready_message,
    channel_output_pump,
    drain_and_deliver_user_chat_turn,
    flush_scope_output_queue_ready,
)
from app.services.agentic_companion.downlink import DownlinkKind


@pytest.fixture(autouse=True)
def _clear_output_queue_registry() -> None:
    clear_output_queues_for_tests()
    yield
    clear_output_queues_for_tests()


def _pending_output_claim(
    *,
    scope: AgentScope,
    message_id: str,
    text: str,
    wire_id: str,
) -> QueueClaim:
    return QueueClaim(
        record=OutputQueueRecord(
            message_id=message_id,
            scope=scope,
            sequence=1,
            status=QueueStatus.PENDING,
            batch_id="batch-1",
            kind=DownlinkKind.USER_REPLY,
            text=text,
            created_at_utc=datetime.now(timezone.utc),
            message_ids=("input-1",),
        ),
        delivery_channel=ChannelKind.TELEGRAM,
        delivery_wire_id=WireId(value=wire_id),
    )


@pytest.mark.asyncio
async def test_concurrent_flush_and_pump_deliver_same_row_twice() -> None:
    """Dual consumers on one row duplicate delivery when flush holds memory pull."""
    scope = AgentScope(user_id="u-dual", agent_id="a-dual")
    wire_id = f"telegram:{scope.registry_key()}"
    message_id = "msg-dual"
    ready = ReadyOutputMessage(
        message_id=message_id,
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="duplicate me",
        sequence=1,
        message_ids=("input-1",),
    )
    queue = get_output_queue_for_scope(scope)
    queue._ready.append(ready)
    deliver_calls: list[str] = []

    async def slow_deliver(message: ReadyOutputMessage) -> None:
        deliver_calls.append(message.message_id)
        if len(deliver_calls) == 1:
            await asyncio.sleep(0.05)

    claim = _pending_output_claim(
        scope=scope,
        message_id=message_id,
        text=ready.text,
        wire_id=wire_id,
    )
    with patch(
        "app.core.companion_harness.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        claim_calls = 0

        async def fake_claim(*_args, **_kwargs):
            nonlocal claim_calls
            if claim_calls == 0:
                claim_calls += 1
                return [claim]
            return []

        repo.claim_pending_for_delivery = AsyncMock(side_effect=fake_claim)
        repo.mark_delivered = AsyncMock()
        with patch(
            "app.core.companion_harness.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            stop = asyncio.Event()
            flush_task = asyncio.create_task(
                flush_scope_output_queue_ready(
                    scope,
                    deliver_message=slow_deliver,
                )
            )
            await asyncio.sleep(0)
            pump_task = asyncio.create_task(
                channel_output_pump(
                    scope,
                    deliver_message=slow_deliver,
                    stop_event=stop,
                    delivery_channel=ChannelKind.TELEGRAM,
                    delivery_wire_id=wire_id,
                    poll_interval_sec=0.01,
                )
            )
            await flush_task
            await asyncio.sleep(0.08)
            stop.set()
            await pump_task

    assert deliver_calls.count(message_id) == 2


@pytest.mark.asyncio
async def test_drain_and_deliver_runs_pump_concurrently() -> None:
    scope = AgentScope(user_id="user-a", agent_id="agent-a")

    async def deliver_message(_message: ReadyOutputMessage) -> None:
        return None

    with patch(
        "app.services.agentic_channel.serving.drain_scope_once_via_companion",
        new_callable=AsyncMock,
        return_value=DrainScopeOnceResult(
            reply_text="hello from companion",
            tool_background_started=False,
            batch_drained=True,
            input_message_ids=("msg-1",),
        ),
    ):
        with patch(
            "app.services.agentic_channel.serving.channel_output_pump",
            new_callable=AsyncMock,
            return_value="hello from pump",
        ) as pump_mock:
            result = await drain_and_deliver_user_chat_turn(
                scope,
                runtime_channel=ChannelKind.TELEGRAM,
                delivery_wire_id="telegram:user-a:agent-a",
                implicit_signal_bundle=ImplicitSignalBundle(
                    client_time=None,
                    user_signed_on=False,
                    server_received_at_utc=None,
                ),
                background_output_sink=None,
                deliver_message=deliver_message,
            )

    assert result == UserChatTurnDeliveryResult(
        delivered_text="hello from pump",
        tool_background_started=False,
    )
    pump_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_drain_and_deliver_returns_empty_when_pump_empty() -> None:
    scope = AgentScope(user_id="user-b", agent_id="agent-b")

    with patch(
        "app.services.agentic_channel.serving.drain_scope_once_via_companion",
        new_callable=AsyncMock,
        return_value=DrainScopeOnceResult(
            reply_text="fallback reply",
            tool_background_started=False,
            batch_drained=True,
            input_message_ids=("msg-2",),
        ),
    ):
        with patch(
            "app.services.agentic_channel.serving.channel_output_pump",
            new_callable=AsyncMock,
            return_value="",
        ):
            result = await drain_and_deliver_user_chat_turn(
                scope,
                runtime_channel=ChannelKind.WECHAT_WEIXIN,
                delivery_wire_id="weixin:binding-1",
                implicit_signal_bundle=ImplicitSignalBundle(
                    client_time=None,
                    user_signed_on=False,
                    server_received_at_utc=None,
                ),
                background_output_sink=None,
                deliver_message=AsyncMock(),
            )

    assert result.delivered_text == ""
    assert result.tool_background_started is False


@pytest.mark.asyncio
async def test_channel_output_pump_delivers_ready_batch_and_acks() -> None:
    scope = AgentScope(user_id="user-c", agent_id="agent-c")
    sent: list[str] = []

    async def deliver_message(message: ReadyOutputMessage) -> None:
        sent.append(message.text)

    ready = ReadyOutputMessage(
        message_id="msg-1",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="queued reply",
        sequence=1,
        message_ids=("input-1",),
    )

    fake_queue = MagicMock()
    fake_queue.pull_ready_batch = AsyncMock(
        side_effect=chain([[ready]], repeat(()))
    )
    fake_queue.ack_delivered = AsyncMock()
    stop = asyncio.Event()
    with patch(
        "app.services.agentic_channel.serving.get_output_queue_for_scope",
        return_value=fake_queue,
    ):
        task = asyncio.create_task(
            channel_output_pump(
                scope, deliver_message=deliver_message, stop_event=stop
            )
        )
        await asyncio.sleep(0.05)
        stop.set()
        last = await task

    assert last == "queued reply"
    assert sent == ["queued reply"]
    fake_queue.ack_delivered.assert_awaited()


@pytest.mark.asyncio
async def test_deliver_ready_message_skips_unroutable_output() -> None:
    scope = AgentScope(user_id="user-skip", agent_id="agent-skip")
    message = ReadyOutputMessage(
        message_id="msg-skip",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="orphan reply",
        sequence=1,
        message_ids=("queue-msg-1",),
    )

    async def deliver_message(_message: ReadyOutputMessage) -> None:
        raise OutputDeliveryUnroutableError(scope, ("queue-msg-1",))

    fake_queue = MagicMock()
    fake_queue.skip_delivery = AsyncMock()
    with patch(
        "app.services.agentic_channel.serving.get_output_queue_for_scope",
        return_value=fake_queue,
    ):
        result = await _deliver_ready_message(
            message=message,
            deliver_message=deliver_message,
            scope=scope,
        )

    assert result is None
    fake_queue.skip_delivery.assert_awaited_once()
    fake_queue.mark_delivery_failed.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_ready_message_retries_transport_failure() -> None:
    scope = AgentScope(user_id="user-retry", agent_id="agent-retry")
    message = ReadyOutputMessage(
        message_id="msg-retry",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="retry reply",
        sequence=1,
        message_ids=("queue-msg-1",),
    )

    async def deliver_message(_message: ReadyOutputMessage) -> None:
        raise RuntimeError("transport broken")

    fake_queue = MagicMock()
    fake_queue.mark_delivery_failed = AsyncMock()
    with patch(
        "app.services.agentic_channel.serving.get_output_queue_for_scope",
        return_value=fake_queue,
    ):
        result = await _deliver_ready_message(
            message=message,
            deliver_message=deliver_message,
            scope=scope,
        )

    assert result is None
    fake_queue.mark_delivery_failed.assert_awaited_once()
    fake_queue.skip_delivery.assert_not_called()
