"""Tests for user-chat drain + OutputQueue pull delivery glue."""

from __future__ import annotations

import asyncio
from itertools import chain, repeat
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.serving import (
    DrainScopeOnceResult,
    UserChatTurnDeliveryResult,
    channel_output_pump,
    drain_and_deliver_user_chat_turn,
)


@pytest.mark.asyncio
async def test_drain_and_deliver_runs_pump_concurrently() -> None:
    scope = AgentScope(user_id="user-a", agent_id="agent-a")
    sent: list[str] = []

    async def send_text(text: str) -> None:
        sent.append(text)

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
                runtime_channel=CompanionRuntimeChannel.TELEGRAM,
                delivery_wire_id="telegram:user-a:agent-a",
                implicit_signal_bundle=ImplicitSignalBundle(
                    client_time=None,
                    user_signed_on=False,
                    server_received_at_utc=None,
                ),
                background_output_sink=None,
                send_text=send_text,
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
                runtime_channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
                delivery_wire_id="weixin:binding-1",
                implicit_signal_bundle=ImplicitSignalBundle(
                    client_time=None,
                    user_signed_on=False,
                    server_received_at_utc=None,
                ),
                background_output_sink=None,
                send_text=AsyncMock(),
            )

    assert result.delivered_text == ""
    assert result.tool_background_started is False


@pytest.mark.asyncio
async def test_channel_output_pump_delivers_ready_batch_and_acks() -> None:
    scope = AgentScope(user_id="user-c", agent_id="agent-c")
    sent: list[str] = []

    async def send_text(text: str) -> None:
        sent.append(text)

    class _Ready:
        message_id = "msg-1"
        text = "queued reply"

    fake_queue = MagicMock()
    fake_queue.pull_ready_batch = AsyncMock(
        side_effect=chain([(_Ready(),)], repeat(()))
    )
    fake_queue.ack_delivered = AsyncMock()
    stop = asyncio.Event()
    with patch(
        "app.services.agentic_channel.serving.get_output_queue_for_scope",
        return_value=fake_queue,
    ):
        task = asyncio.create_task(
            channel_output_pump(scope, send_text=send_text, stop_event=stop)
        )
        await asyncio.sleep(0.05)
        stop.set()
        last = await task

    assert last == "queued reply"
    assert sent == ["queued reply"]
    fake_queue.ack_delivered.assert_awaited()
