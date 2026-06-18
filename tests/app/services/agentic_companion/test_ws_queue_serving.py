"""Tests for App WebSocket queue serving helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.serving import UserChatTurnDeliveryResult
from app.services.agentic_companion.ws_queue_serving import (
    AppWsQueueDeliveryFlags,
    AppWsUserTurnQueueInput,
    run_app_ws_user_turn_via_queues,
)


@pytest.mark.asyncio
async def test_run_app_ws_user_turn_via_queues_enqueues_and_delivers() -> None:
    scope = AgentScope(user_id="user-ws", agent_id="agent-ws")
    flags = AppWsQueueDeliveryFlags()
    sent: list[str] = []

    async def send_text(text: str) -> None:
        sent.append(text)

    queue_input = AppWsUserTurnQueueInput(
        scope=scope,
        wire_id="app:conn-1",
        user_text="hello ws",
        client_message_id="11111111-1111-4111-8111-111111111111",
        implicit_signal_bundle=ImplicitSignalBundle(
            client_time=None,
            user_signed_on=False,
            server_received_at_utc=None,
        ),
        background_output_sink=None,
        delivery_flags=flags,
        send_text=send_text,
    )

    with (
        patch(
            "app.services.agentic_companion.ws_queue_serving.enqueue_inbound_wire_message",
            new_callable=AsyncMock,
            return_value="queue-msg-1",
        ) as enqueue_mock,
        patch(
            "app.services.agentic_companion.ws_queue_serving.ensure_memory_store_session",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.agentic_companion.ws_queue_serving.image_asset_baseline_for_scope_store",
            return_value=2,
        ),
        patch(
            "app.services.agentic_companion.ws_queue_serving.drain_and_deliver_user_chat_turn",
            new_callable=AsyncMock,
            return_value=UserChatTurnDeliveryResult(
                delivered_text="companion reply",
                tool_background_started=False,
            ),
        ) as deliver_mock,
    ):
        result = await run_app_ws_user_turn_via_queues(queue_input)

    assert result == UserChatTurnDeliveryResult(
        delivered_text="companion reply",
        tool_background_started=False,
    )
    assert flags.queue_message_id == "queue-msg-1"
    assert flags.image_asset_baseline == 2
    assert flags.image_asset_baseline_initialized is True
    assert flags.tool_background_started is False
    enqueue_mock.assert_awaited_once()
    inbound = enqueue_mock.await_args.args[0]
    assert inbound.channel == CompanionRuntimeChannel.APP
    assert inbound.wire_id == "app:conn-1"
    assert inbound.client_message_id == "11111111-1111-4111-8111-111111111111"
    deliver_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_app_ws_user_turn_via_queues_propagates_tool_background_flag() -> None:
    scope = AgentScope(user_id="user-ws", agent_id="agent-ws")
    flags = AppWsQueueDeliveryFlags()

    queue_input = AppWsUserTurnQueueInput(
        scope=scope,
        wire_id="app:conn-2",
        user_text="paint",
        client_message_id="22222222-2222-4222-8222-222222222222",
        implicit_signal_bundle=ImplicitSignalBundle(
            client_time=None,
            user_signed_on=False,
            server_received_at_utc=None,
        ),
        background_output_sink=None,
        delivery_flags=flags,
        send_text=AsyncMock(),
    )

    with (
        patch(
            "app.services.agentic_companion.ws_queue_serving.enqueue_inbound_wire_message",
            new_callable=AsyncMock,
            return_value="queue-msg-2",
        ),
        patch(
            "app.services.agentic_companion.ws_queue_serving.ensure_memory_store_session",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.agentic_companion.ws_queue_serving.image_asset_baseline_for_scope_store",
            return_value=0,
        ),
        patch(
            "app.services.agentic_companion.ws_queue_serving.drain_and_deliver_user_chat_turn",
            new_callable=AsyncMock,
            return_value=UserChatTurnDeliveryResult(
                delivered_text="tb-reply",
                tool_background_started=True,
            ),
        ),
    ):
        result = await run_app_ws_user_turn_via_queues(queue_input)

    assert result.tool_background_started is True
    assert flags.tool_background_started is True
    assert flags.image_asset_baseline_initialized is True
    assert flags.queue_message_id == "queue-msg-2"
