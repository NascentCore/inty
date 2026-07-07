"""Tests for AgentChannelPresence ScopeQueueServing lifecycle and Telegram inbound."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.companion_harness.agentic_companion.types import OutputMessageKind
from app.services.agentic_channel.channel_runtime import (
    clear_registries_for_tests,
)
from app.services.agentic_channel.scope_queue_serving import (
    ScopeDrainCompletion,
)
from app.services.agentic_channel.presence import (
    AgentChannelPresence,
    clear_presences_for_tests,
    ensure_presence,
    stop_presence,
)


@pytest.fixture(autouse=True)
def _clear_presence_registry() -> None:
    clear_presences_for_tests()
    clear_registries_for_tests()


@pytest.mark.asyncio
async def test_ensure_presence_starts_queue_serving_once() -> None:
    scope = AgentScope(user_id="user-presence", agent_id="agent-presence")
    with patch(
        "app.services.agentic_channel.presence.ScopeQueueServing.start",
        new_callable=AsyncMock,
    ) as queue_start_mock:
        presence_a = await ensure_presence(scope)
        presence_b = await ensure_presence(scope)
        await stop_presence(scope)

    assert presence_a is presence_b
    queue_start_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_presence_stops_queue_serving() -> None:
    scope = AgentScope(
        user_id="user-stop-presence", agent_id="agent-stop-presence"
    )
    with patch(
        "app.services.agentic_channel.presence.ScopeQueueServing.stop",
        new_callable=AsyncMock,
    ) as queue_stop_mock:
        await ensure_presence(scope)
        await stop_presence(scope)

    queue_stop_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_user_text_enqueues_and_wakes_without_drain() -> None:
    scope = AgentScope(user_id="user-inbound", agent_id="agent-inbound")
    presence = AgentChannelPresence(scope)
    wake_mock = MagicMock()
    presence._queue_serving = MagicMock()
    presence._queue_serving.wake = wake_mock

    inty_user = MagicMock()
    agent_data = MagicMock()

    with patch(
        "app.services.agentic_channel.presence.AsyncSessionLocal"
    ) as session_local:
        db = AsyncMock()
        session_local.return_value.__aenter__.return_value = db
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = inty_user
        db.execute = AsyncMock(return_value=user_result)
        with patch(
            "app.services.agentic_channel.presence.agent_service.get_agent_for_chat",
            new_callable=AsyncMock,
            return_value=agent_data,
        ):
            with patch(
                "app.services.agentic_channel.presence.enqueue_inbound_wire_message",
                new_callable=AsyncMock,
                return_value="queued-msg-1",
            ) as enqueue_mock:
                with patch(
                    "app.services.agentic_channel.serving.drain_and_deliver_user_chat_turn",
                    new_callable=AsyncMock,
                ) as drain_mock:
                    reply = await presence.handle_user_text(
                        "hello",
                        runtime_channel=ChannelKind.TELEGRAM,
                    )

    assert reply == ""
    enqueue_mock.assert_awaited_once()
    wake_mock.assert_called_once_with(runtime_channel=ChannelKind.TELEGRAM)
    drain_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_queue_drain_complete_keeps_only_tool_background_anchor() -> None:
    scope = AgentScope(user_id="user-cleanup", agent_id="agent-cleanup")
    presence = AgentChannelPresence(scope)
    presence._coordinator.set_foreground_pending("m1", {"value": 1})
    presence._coordinator.set_foreground_pending("m2", {"value": 2})
    presence._coordinator.set_foreground_pending("m3", {"value": 3})

    await presence._on_queue_drain_complete(
        ScopeDrainCompletion(
            input_message_ids=("m1", "m2", "m3"),
            tool_background_started=True,
        )
    )

    assert not presence._coordinator.has_foreground_pending("m1")
    assert not presence._coordinator.has_foreground_pending("m2")
    assert presence._coordinator.has_foreground_pending("m3")


@pytest.mark.asyncio
async def test_queue_drain_complete_removes_all_without_tool_background() -> (
    None
):
    scope = AgentScope(user_id="user-cleanup-all", agent_id="agent-cleanup-all")
    presence = AgentChannelPresence(scope)
    presence._coordinator.set_foreground_pending("m1", {"value": 1})
    presence._coordinator.set_foreground_pending("m2", {"value": 2})

    await presence._on_queue_drain_complete(
        ScopeDrainCompletion(
            input_message_ids=("m1", "m2"),
            tool_background_started=False,
        )
    )

    assert not presence._coordinator.has_foreground_pending("m1")
    assert not presence._coordinator.has_foreground_pending("m2")


@pytest.mark.asyncio
async def test_enqueue_app_ws_user_turn_enqueues_durable_app_metadata() -> None:
    scope = AgentScope(user_id="user-app-pending", agent_id="agent-app-pending")
    presence = AgentChannelPresence(scope)
    presence._queue_serving = MagicMock()

    with patch(
        "app.services.agentic_channel.presence.enqueue_inbound_wire_message",
        new_callable=AsyncMock,
        return_value="client-app-pending",
    ) as enqueue_mock:
        queue_message_id = await presence.enqueue_app_ws_user_turn(
            wire_id="app:wire-pending",
            user_text="hi",
            client_message_id="client-app-pending",
            local_id="local-app-pending",
            chat_history_user_row_id=42,
        )

    assert queue_message_id == "client-app-pending"
    inbound = enqueue_mock.await_args.args[0]
    assert inbound.client_message_id == "client-app-pending"
    assert inbound.local_id == "local-app-pending"
    assert inbound.chat_history_user_row_id == 42
    assert not presence._coordinator.foreground_pending


@pytest.mark.asyncio
async def test_send_user_reply_without_active_channel_raises_for_output_retry() -> (
    None
):
    scope = AgentScope(user_id="user-no-active", agent_id="agent-no-active")
    presence = AgentChannelPresence(scope)
    message = ReadyOutputMessage(
        message_id="out-1",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="hello",
        message_ids=("m1",),
        sequence=1,
    )

    with pytest.raises(RuntimeError, match="no ACTIVE channel"):
        await presence._deliver_ready_via_active_channel(message)


@pytest.mark.asyncio
async def test_tool_background_without_input_ids_raises_unroutable() -> None:
    scope = AgentScope(user_id="user-tool-hidden", agent_id="agent-tool-hidden")
    presence = AgentChannelPresence(scope)
    message = ReadyOutputMessage(
        message_id="out-tool",
        batch_id="agent-initiated:tool",
        kind=OutputMessageKind.TOOL_BACKGROUND,
        text="tool follow-up",
        message_ids=(),
        sequence=1,
    )

    with pytest.raises(OutputDeliveryUnroutableError):
        await presence._deliver_ready_via_active_channel(message)


@pytest.mark.asyncio
async def test_handle_user_text_returns_validation_error_before_enqueue() -> (
    None
):
    scope = AgentScope(user_id="user-missing", agent_id="agent-missing")
    presence = AgentChannelPresence(scope)
    presence._queue_serving = MagicMock()

    with patch(
        "app.services.agentic_channel.presence.AsyncSessionLocal"
    ) as session_local:
        db = AsyncMock()
        session_local.return_value.__aenter__.return_value = db
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=user_result)
        with patch(
            "app.services.agentic_channel.presence.enqueue_inbound_wire_message",
            new_callable=AsyncMock,
        ) as enqueue_mock:
            reply = await presence.handle_user_text(
                "hello",
                runtime_channel=ChannelKind.TELEGRAM,
            )

    assert "Could not find your Inty user" in reply
    enqueue_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_telegram_user_chat_enqueues_inbound_in_user_language() -> None:
    scope = AgentScope(user_id="user-lang", agent_id="agent-lang")
    presence = AgentChannelPresence(scope)
    wake_mock = MagicMock()
    presence._queue_serving = MagicMock()
    presence._queue_serving.wake = wake_mock

    inty_user = MagicMock()
    agent_data = MagicMock()

    with patch(
        "app.services.agentic_channel.presence.AsyncSessionLocal"
    ) as session_local:
        db = AsyncMock()
        session_local.return_value.__aenter__.return_value = db
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = inty_user
        db.execute = AsyncMock(return_value=user_result)
        with patch(
            "app.services.agentic_channel.presence.agent_service.get_agent_for_chat",
            new_callable=AsyncMock,
            return_value=agent_data,
        ):
            with patch(
                "app.services.agentic_channel.presence.enqueue_inbound_wire_message",
                new_callable=AsyncMock,
                return_value="queued-msg-cn",
            ) as enqueue_mock:
                reply = await presence.handle_user_text(
                    "你好",
                    runtime_channel=ChannelKind.TELEGRAM,
                )

    assert reply == ""
    inbound = enqueue_mock.await_args.args[0]
    assert inbound.text == "你好"
    wake_mock.assert_called_once_with(runtime_channel=ChannelKind.TELEGRAM)
