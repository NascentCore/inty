"""Tests for App WebSocket queue serving helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
)
from app.services.agentic_companion.downlink import DownlinkKind
from app.services.agentic_channel.serving import _deliver_ready_message
from app.services.agentic_companion.ws_queue_serving import (
    AppWsQueueDeliveryFlags,
    AppWsUserTurnEnqueueResult,
    AppWsUserTurnQueueInput,
    _lookup_scope_turn_delivery,
    _make_on_drain_complete,
    _on_app_ws_scope_drain_complete,
    _register_scope_turn_delivery,
    _scope_deliver_ready_output,
    clear_app_ws_scope_queue_for_tests,
    enqueue_app_ws_user_turn_and_wake,
    stop_app_ws_scope_queue_serving,
)
from app.services.agentic_channel.scope_queue_serving import (
    ScopeDrainCompletion,
)


@pytest.fixture(autouse=True)
def _clear_ws_scope_queue_registry() -> None:
    clear_app_ws_scope_queue_for_tests()


def _ready_message(
    *,
    text: str,
    message_ids: tuple[str, ...],
) -> ReadyOutputMessage:
    return ReadyOutputMessage(
        message_id="msg-ready",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text=text,
        sequence=1,
        message_ids=message_ids,
    )


@pytest.mark.asyncio
async def test_enqueue_app_ws_user_turn_and_wake_without_drain() -> None:
    scope = AgentScope(user_id="user-ws", agent_id="agent-ws")
    flags = AppWsQueueDeliveryFlags()
    sent: list[str] = []

    async def send_text(message: ReadyOutputMessage) -> None:
        sent.append(message.text)

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
    wake_mock.assert_called_once_with(
        runtime_channel=CompanionRuntimeChannel.APP
    )
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
async def test_drain_complete_clears_only_matching_queue_message_state() -> (
    None
):
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
    assert _lookup_scope_turn_delivery(scope, "queue-msg-a") is not None
    assert _lookup_scope_turn_delivery(scope, "queue-msg-b") is not None


@pytest.mark.asyncio
async def test_tool_background_drain_keeps_primary_delivery_hook_for_late_output() -> (
    None
):
    scope = AgentScope(user_id="user-late", agent_id="agent-late")
    sent: list[str] = []

    async def send_text(message: ReadyOutputMessage) -> None:
        sent.append(message.text)

    _register_scope_turn_delivery(
        scope,
        "queue-msg-late",
        send_text=send_text,
        delivery_flags=AppWsQueueDeliveryFlags(
            queue_message_id="queue-msg-late"
        ),
        client_message_id="client-late",
        companion_ws_foreground_pending=None,
    )

    await _on_app_ws_scope_drain_complete(
        scope,
        ScopeDrainCompletion(
            input_message_ids=("queue-msg-late",),
            tool_background_started=True,
        ),
    )
    await _scope_deliver_ready_output(
        scope,
        _ready_message(
            text="late trailing reply", message_ids=("queue-msg-late",)
        ),
    )

    assert sent == ["late trailing reply"]
    assert _lookup_scope_turn_delivery(scope, "queue-msg-late") is not None


@pytest.mark.asyncio
async def test_deliver_ready_output_raises_when_hook_missing() -> None:
    scope = AgentScope(user_id="user-missing", agent_id="agent-missing")
    with pytest.raises(OutputDeliveryUnroutableError) as exc_info:
        await _scope_deliver_ready_output(
            scope,
            _ready_message(
                text="orphan reply", message_ids=("missing-queue-msg",)
            ),
        )
    assert exc_info.value.message_ids == ("missing-queue-msg",)


@pytest.mark.asyncio
async def test_deliver_ready_output_raises_when_message_ids_empty() -> None:
    scope = AgentScope(user_id="user-empty", agent_id="agent-empty")
    with pytest.raises(OutputDeliveryUnroutableError) as exc_info:
        await _scope_deliver_ready_output(
            scope,
            _ready_message(text="orphan reply", message_ids=()),
        )
    assert exc_info.value.message_ids == ()


@pytest.mark.asyncio
async def test_deliver_ready_output_routes_by_input_message_ids() -> None:
    scope = AgentScope(user_id="user-route", agent_id="agent-route")
    sent_by_turn: dict[str, list[str]] = {"a": [], "b": []}

    async def send_a(message: ReadyOutputMessage) -> None:
        sent_by_turn["a"].append(message.text)

    async def send_b(message: ReadyOutputMessage) -> None:
        sent_by_turn["b"].append(message.text)

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
        _ready_message(text="reply for a", message_ids=("queue-msg-a",)),
    )
    await _scope_deliver_ready_output(
        scope,
        _ready_message(text="reply for b", message_ids=("queue-msg-b",)),
    )

    assert sent_by_turn["a"] == ["reply for a"]
    assert sent_by_turn["b"] == ["reply for b"]


@pytest.mark.asyncio
async def test_deliver_ready_output_survives_drain_complete() -> None:
    """Regression (REPL race): drain completion must keep WS send routing alive."""
    scope = AgentScope(user_id="user-race", agent_id="agent-race")
    input_id = "queue-msg-race"
    sent: list[str] = []

    async def send_text(message: ReadyOutputMessage) -> None:
        sent.append(message.text)

    _register_scope_turn_delivery(
        scope,
        input_id,
        send_text=send_text,
        delivery_flags=AppWsQueueDeliveryFlags(queue_message_id=input_id),
        client_message_id="client-race",
        companion_ws_foreground_pending=None,
    )

    await _on_app_ws_scope_drain_complete(
        scope,
        ScopeDrainCompletion(
            input_message_ids=(input_id,),
            tool_background_started=False,
        ),
    )

    await _scope_deliver_ready_output(
        scope,
        _ready_message(
            text="reply after drain complete", message_ids=(input_id,)
        ),
    )

    assert sent == ["reply after drain complete"]


@pytest.mark.asyncio
async def test_deliver_ready_message_delivers_after_drain_complete() -> None:
    """Output pump delivers and acks a reply pumped after drain completion."""
    scope = AgentScope(user_id="user-pump-race", agent_id="agent-pump-race")
    input_id = "queue-msg-pump-race"
    sent: list[str] = []

    async def send_text(message: ReadyOutputMessage) -> None:
        sent.append(message.text)

    _register_scope_turn_delivery(
        scope,
        input_id,
        send_text=send_text,
        delivery_flags=AppWsQueueDeliveryFlags(queue_message_id=input_id),
        client_message_id="client-pump-race",
        companion_ws_foreground_pending=None,
    )
    on_drain_complete = _make_on_drain_complete(scope)
    await on_drain_complete(
        ScopeDrainCompletion(
            input_message_ids=(input_id,),
            tool_background_started=False,
        ),
    )

    async def deliver_message(message: ReadyOutputMessage) -> None:
        await _scope_deliver_ready_output(scope, message)

    fake_queue = MagicMock()
    fake_queue.ack_delivered = AsyncMock()
    fake_queue.mark_delivery_failed = AsyncMock()
    ready = ReadyOutputMessage(
        message_id="out-race-1",
        batch_id="batch-race-1",
        kind=DownlinkKind.USER_REPLY,
        text="queued bootstrap reply",
        sequence=1,
        message_ids=(input_id,),
    )
    with patch(
        "app.services.agentic_channel.serving.get_output_queue_for_scope",
        return_value=fake_queue,
    ):
        delivered = await _deliver_ready_message(
            message=ready,
            deliver_message=deliver_message,
            scope=scope,
        )

    assert delivered == "queued bootstrap reply"
    assert sent == ["queued bootstrap reply"]
    fake_queue.mark_delivery_failed.assert_not_awaited()
    fake_queue.ack_delivered.assert_awaited_once()
    ack = fake_queue.ack_delivered.await_args.args[0]
    assert ack.message_id == "out-race-1"


@pytest.mark.asyncio
async def test_background_reply_delivers_after_drain_complete() -> None:
    """Background tool replies arrive after drain completion under the same input id."""
    scope = AgentScope(user_id="user-bg", agent_id="agent-bg")
    input_id = "queue-msg-bg"
    sent: list[str] = []

    async def send_text(message: ReadyOutputMessage) -> None:
        sent.append(message.text)

    _register_scope_turn_delivery(
        scope,
        input_id,
        send_text=send_text,
        delivery_flags=AppWsQueueDeliveryFlags(queue_message_id=input_id),
        client_message_id="client-bg",
        companion_ws_foreground_pending=None,
    )

    await _on_app_ws_scope_drain_complete(
        scope,
        ScopeDrainCompletion(
            input_message_ids=(input_id,),
            tool_background_started=True,
        ),
    )

    await _scope_deliver_ready_output(
        scope,
        _ready_message(text="foreground reply", message_ids=(input_id,)),
    )
    await _scope_deliver_ready_output(
        scope,
        _ready_message(text="background tool reply", message_ids=(input_id,)),
    )

    assert sent == ["foreground reply", "background tool reply"]


@pytest.mark.asyncio
async def test_tool_background_drain_clears_non_primary_client_aliases() -> (
    None
):
    """Only the primary input id remains pending while background tools run."""
    scope = AgentScope(user_id="user-bg-clean", agent_id="agent-bg-clean")
    pending: dict[str, dict[str, str]] = {
        "client-a": {"turn": "a"},
        "queue-msg-a": {"turn": "a"},
        "client-b": {"turn": "b"},
        "queue-msg-b": {"turn": "b"},
    }
    _register_scope_turn_delivery(
        scope,
        "queue-msg-a",
        send_text=AsyncMock(),
        delivery_flags=AppWsQueueDeliveryFlags(queue_message_id="queue-msg-a"),
        client_message_id="client-a",
        companion_ws_foreground_pending=pending,
    )
    _register_scope_turn_delivery(
        scope,
        "queue-msg-b",
        send_text=AsyncMock(),
        delivery_flags=AppWsQueueDeliveryFlags(queue_message_id="queue-msg-b"),
        client_message_id="client-b",
        companion_ws_foreground_pending=pending,
    )

    await _on_app_ws_scope_drain_complete(
        scope,
        ScopeDrainCompletion(
            input_message_ids=("queue-msg-a", "queue-msg-b"),
            tool_background_started=True,
        ),
    )

    assert "client-a" not in pending
    assert "queue-msg-a" not in pending
    assert "client-b" not in pending
    assert pending["queue-msg-b"] == {"turn": "b"}
