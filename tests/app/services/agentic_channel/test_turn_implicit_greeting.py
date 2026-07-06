"""Tests for agent-channel sign-on greeting via presence."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.services.agentic_channel.presence import AgentChannelPresence


@pytest.mark.asyncio
async def test_greet_on_sign_on_hands_output_queue_to_turn() -> None:
    """Presence passes the scope OutputQueue and a synthetic batch into the turn.

    Visible text is appended by AgenticLoop inside the turn (see
    ``test_greet_on_sign_on_delivery``), not by presence after it.
    """
    scope = AgentScope(user_id="user-greet", agent_id="agent-greet")
    presence = AgentChannelPresence(scope)
    fake_model = MagicMock()
    fake_queue = MagicMock()
    fake_queue.append_visible_message = AsyncMock()

    with patch(
        "app.services.agentic_channel.presence.resolve_chat_model_for_scope",
        new_callable=AsyncMock,
        return_value=fake_model,
    ) as resolve_mock:
        with patch(
            "app.services.agentic_channel.presence.run_companion_implicit_sign_on_greeting_turn_for_api",
            new_callable=AsyncMock,
            return_value=CompanionTurnResult(assistant_text="Hello from Inty."),
        ) as api_mock:
            with patch(
                "app.services.agentic_channel.presence.get_output_queue_for_scope",
                return_value=fake_queue,
            ):
                await presence.greet_on_sign_on(
                    runtime_channel=ChannelKind.TELEGRAM,
                )

    resolve_mock.assert_awaited_once_with(scope)
    api_mock.assert_awaited_once()
    kwargs = api_mock.await_args.kwargs
    assert kwargs["user_id"] == scope.user_id
    assert kwargs["agent_id"] == scope.agent_id
    assert kwargs["chat_id"] == scope.memory_store_chat_id()
    assert kwargs["user_text"] != ""
    assert "/start" not in kwargs["user_text"]
    assert kwargs["resolved_chat_model"] is fake_model
    assert kwargs["runtime_channel"] == ChannelKind.TELEGRAM
    assert kwargs["implicit_signal_bundle"].user_signed_on is True
    assert kwargs["implicit_signal_bundle"].server_received_at_utc is not None
    assert kwargs["agentic_output_queue"] is fake_queue
    batch = kwargs["user_message_batch"]
    assert batch.batch_id.startswith(
        "agent-initiated:implicit_sign_on_greeting:"
    )
    assert batch.message_ids == (kwargs["preset_user_msg_uuid"],)
    # Presence must not append visible text itself; AgenticLoop owns the append.
    fake_queue.append_visible_message.assert_not_awaited()
