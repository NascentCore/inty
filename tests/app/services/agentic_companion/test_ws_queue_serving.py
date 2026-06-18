"""Tests for App WebSocket queue serving helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_companion.ws_queue_serving import (
    AppWsQueueDeliveryFlags,
    AppWsUserTurnEnqueueResult,
    AppWsUserTurnQueueInput,
    _on_app_ws_scope_drain_complete,
    _register_scope_turn_delivery,
    _scope_deliver_ready_output,
    clear_app_ws_scope_queue_for_tests,
    enqueue_app_ws_user_turn_and_wake,
    stop_app_ws_scope_queue_serving,
)
from app.services.agentic_channel.scope_queue_serving import ScopeDrainCompletion


@pytest.fixture(autouse=True)
def _clear_ws_scope_queue_registry() -> None:
    clear_app_ws_scope_queue_for_tests()


@pytest.mark.asyncio
async def test_enqueue_app_ws_user_turn_and_wake_without_drain() -> None:
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
    wake_mock = MagicMock()
    serving_mock = MagicMock()
    serving_mock.wake = wake_mock

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
            "app.services.agentic_companion.ws_queue_serving._ensure_app_ws_scope_queue_serving",
            new_callable=AsyncMock,
            return_value=serving_mock,
        ) as ensure_mock,
        patch(
            "app.services.agentic_channel.serving.drain_and_deliver_user_chat_turn",
            new_callable=AsyncMock,
        ) as drain_mock,
    ):
        result = await enqueue_app_ws_user_turn_and_wake(
            queue_input,
            companion_ws_foreground_pending={},
        )

    assert result == AppWsUserTurnEnqueueResult(queue_message_id="queue-msg-1")
    assert flags.queue_message_id == "queue-msg-1"
    assert flags.image_asset_baseline == 2
    assert flags.image_asset_baseline_initialized is True
    assert sent == []
    enqueue_mock.assert_awaited_once()
    inbound = enqueue_mock.await_args.args[0]
    assert inbound.channel == CompanionRuntimeChannel.APP
    assert inbound.wire_id == "app:conn-1"
    assert inbound.client_message_id == "11111111-1111-4111-8111-111111111111"
    ensure_mock.assert_awaited_once()
    wake_mock.assert_called_once_with(runtime_channel=CompanionRuntimeChannel.APP)
    drain_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_stop_app_ws_scope_queue_serving_clears_registry() -> None:
    scope = AgentScope(user_id="user-stop", agent_id="agent-stop")
    stop_mock = AsyncMock()

    with (
        patch(
            "app.services.agentic_companion.ws_queue_serving.enqueue_inbound_wire_message",
            new_callable=AsyncMock,
            return_value="queue-msg-stop",
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
            "app.services.agentic_companion.ws_queue_serving.ScopeQueueServing.start",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.agentic_companion.ws_queue_serving.ScopeQueueServing.stop",
            new_callable=AsyncMock,
            side_effect=stop_mock,
        ),
    ):
        await enqueue_app_ws_user_turn_and_wake(
            AppWsUserTurnQueueInput(
                scope=scope,
                wire_id="app:conn-2",
                user_text="hi",
                client_message_id=None,
                implicit_signal_bundle=ImplicitSignalBundle(
                    client_time=None,
                    user_signed_on=False,
                    server_received_at_utc=None,
                ),
                background_output_sink=None,
                delivery_flags=AppWsQueueDeliveryFlags(),
                send_text=AsyncMock(),
            ),
            companion_ws_foreground_pending=None,
        )
        await stop_app_ws_scope_queue_serving(scope)

    stop_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_drain_complete_clears_only_matching_queue_message_state() -> None:
    scope = AgentScope(user_id="user-conc", agent_id="agent-conc")
    pending: dict[str, dict[str, str]] = {
        "client-a": {"turn": "a"},
        "queue-msg-a": {"turn": "a"},
        "client-b": {"turn": "b"},
        "queue-msg-b": {"turn": "b"},
    }
    flags_a = AppWsQueueDeliveryFlags(queue_message_id="queue-msg-a")
    flags_b = AppWsQueueDeliveryFlags(queue_message_id="queue-msg-b")
    _register_scope_turn_delivery(
        scope,
        "queue-msg-a",
        send_text=AsyncMock(),
        delivery_flags=flags_a,
        client_message_id="client-a",
        companion_ws_foreground_pending=pending,
    )
    _register_scope_turn_delivery(
        scope,
        "queue-msg-b",
        send_text=AsyncMock(),
        delivery_flags=flags_b,
        client_message_id="client-b",
        companion_ws_foreground_pending=pending,
    )

    await _on_app_ws_scope_drain_complete(
        scope,
        ScopeDrainCompletion(
            input_message_ids=("queue-msg-a",),
            tool_background_started=False,
        ),
    )

    assert "client-a" not in pending
    assert "queue-msg-a" not in pending
    assert pending["client-b"] == {"turn": "b"}
    assert pending["queue-msg-b"] == {"turn": "b"}
    assert flags_a.tool_background_started is False
    assert flags_b.tool_background_started is False


@pytest.mark.asyncio
async def test_deliver_ready_output_routes_by_input_message_ids() -> None:
    scope = AgentScope(user_id="user-route", agent_id="agent-route")
    sent_by_turn: dict[str, list[str]] = {"a": [], "b": []}

    async def send_a(text: str) -> None:
        sent_by_turn["a"].append(text)

    async def send_b(text: str) -> None:
        sent_by_turn["b"].append(text)

    _register_scope_turn_delivery(
        scope,
        "queue-msg-a",
        send_text=send_a,
        delivery_flags=AppWsQueueDeliveryFlags(queue_message_id="queue-msg-a"),
        client_message_id="client-a",
        companion_ws_foreground_pending=None,
    )
    _register_scope_turn_delivery(
        scope,
        "queue-msg-b",
        send_text=send_b,
        delivery_flags=AppWsQueueDeliveryFlags(queue_message_id="queue-msg-b"),
        client_message_id="client-b",
        companion_ws_foreground_pending=None,
    )

    await _scope_deliver_ready_output(
        scope,
        "reply for a",
        ("queue-msg-a",),
    )
    await _scope_deliver_ready_output(
        scope,
        "reply for b",
        ("queue-msg-b",),
    )

    assert sent_by_turn["a"] == ["reply for a"]
    assert sent_by_turn["b"] == ["reply for b"]
