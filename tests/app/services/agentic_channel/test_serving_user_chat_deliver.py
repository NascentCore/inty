"""Tests for user-chat drain + OutputQueue pull delivery glue."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.serving import (
    DrainScopeOnceResult,
    UserChatTurnDeliveryResult,
    drain_and_deliver_user_chat_turn,
)


@pytest.mark.asyncio
async def test_drain_and_deliver_returns_delivered_text() -> None:
    scope = AgentScope(user_id="user-a", agent_id="agent-a")
    sent: list[str] = []

    async def send_text(text: str) -> None:
        sent.append(text)

    with (
        patch(
            "app.services.agentic_channel.serving.drain_scope_once_via_companion",
            new_callable=AsyncMock,
            return_value=DrainScopeOnceResult(
                reply_text="hello from companion",
                tool_background_started=False,
            ),
        ),
        patch(
            "app.services.agentic_channel.serving.deliver_pending_output_for_wire",
            new_callable=AsyncMock,
            return_value="hello from companion",
        ) as deliver_mock,
    ):
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
        delivered_text="hello from companion",
        tool_background_started=False,
    )
    deliver_mock.assert_awaited_once()
    assert sent == []


@pytest.mark.asyncio
async def test_drain_and_deliver_send_failure_is_silent() -> None:
    scope = AgentScope(user_id="user-b", agent_id="agent-b")

    async def send_text(_text: str) -> None:
        raise RuntimeError("transport broken")

    with (
        patch(
            "app.services.agentic_channel.serving.drain_scope_once_via_companion",
            new_callable=AsyncMock,
            return_value=DrainScopeOnceResult(
                reply_text="would have replied",
                tool_background_started=False,
            ),
        ),
        patch(
            "app.services.agentic_channel.serving.deliver_pending_output_for_wire",
            new_callable=AsyncMock,
            return_value="",
        ) as deliver_mock,
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
            send_text=send_text,
        )

    assert result.delivered_text == ""
    assert result.tool_background_started is False
    deliver_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_drain_and_deliver_empty_placeholder_via_deliver() -> None:
    scope = AgentScope(user_id="user-c", agent_id="agent-c")

    with (
        patch(
            "app.services.agentic_channel.serving.drain_scope_once_via_companion",
            new_callable=AsyncMock,
            return_value=DrainScopeOnceResult(
                reply_text="（没有回复内容）",
                tool_background_started=False,
            ),
        ),
        patch(
            "app.services.agentic_channel.serving.deliver_pending_output_for_wire",
            new_callable=AsyncMock,
            return_value="（没有回复内容）",
        ),
    ):
        result = await drain_and_deliver_user_chat_turn(
            scope,
            runtime_channel=CompanionRuntimeChannel.TELEGRAM,
            delivery_wire_id="telegram:user-c:agent-c",
            implicit_signal_bundle=ImplicitSignalBundle(
                client_time=None,
                user_signed_on=False,
                server_received_at_utc=None,
            ),
            background_output_sink=None,
            send_text=AsyncMock(),
        )

    assert result.delivered_text == "（没有回复内容）"
