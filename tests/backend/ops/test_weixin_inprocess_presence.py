"""Weixin in-process presence resolves Inty user from JWT, not demo session_id."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.agentic_channel.presence import AgentChannelPresence
from backend.ops.weixin_channel.inprocess_presence import (
    WeixinInprocessPresence,
    _inty_user_from_binding,
)
from backend.ops.weixin_channel.session import WeixinChannelBinding
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_user_for_test,
)


def _binding(agent_id: str = "agent-1") -> WeixinChannelBinding:
    return WeixinChannelBinding(
        user_id="demo-session-uuid",
        agent_id=agent_id,
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt-token",
        weixin_account_id="wx-acct",
        weixin_token="token",
        weixin_base_url="https://ilinkai.weixin.qq.com",
    )


async def _delete_user(user_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_inty_user_from_binding_uses_jwt_not_session_id() -> None:
    binding = _binding()
    fake_user = object()

    with patch(
        "backend.ops.weixin_channel.inprocess_presence.deps.get_user_from_token",
        new_callable=AsyncMock,
        return_value=fake_user,
    ) as mock_get_user:
        out = await _inty_user_from_binding(binding)

    assert out is fake_user
    mock_get_user.assert_awaited_once()
    _token_arg = mock_get_user.await_args.args[0]
    assert _token_arg == "jwt-token"


@pytest.mark.asyncio
async def test_handle_user_text_invalid_jwt_returns_visible_message() -> None:
    presence = WeixinInprocessPresence(_binding())
    fake_user = MagicMock()
    fake_user.id = "user-test"
    with (
        patch(
            "backend.ops.weixin_channel.inprocess_presence._inty_user_from_binding",
            new_callable=AsyncMock,
            return_value=fake_user,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.turn_channel_up",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.ensure_presence",
            new_callable=AsyncMock,
            return_value=MagicMock(spec=AgentChannelPresence),
        ),
    ):
        await presence.start(MagicMock())
    with patch(
        "backend.ops.weixin_channel.inprocess_presence.deps.get_user_from_token",
        new_callable=AsyncMock,
        return_value=None,
    ):
        reply = await presence.handle_user_text("hello")
    assert "JWT" in reply or "token" in reply.lower()


@pytest.mark.asyncio
async def test_start_registers_weixin_channel_and_presence() -> None:
    presence = WeixinInprocessPresence(_binding())
    fake_user = MagicMock()
    fake_user.id = "user-test"
    mock_agent_presence = MagicMock(spec=AgentChannelPresence)

    with (
        patch(
            "backend.ops.weixin_channel.inprocess_presence._inty_user_from_binding",
            new_callable=AsyncMock,
            return_value=fake_user,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.turn_channel_up",
            new_callable=AsyncMock,
        ) as turn_up,
        patch(
            "backend.ops.weixin_channel.inprocess_presence.ensure_presence",
            new_callable=AsyncMock,
            return_value=mock_agent_presence,
        ) as ensure,
    ):
        await presence.start(MagicMock())

    assert presence._scope == AgentScope(
        user_id="user-test", agent_id="agent-1"
    )
    turn_up.assert_awaited_once()
    ensure.assert_awaited_once_with(presence._scope)


@pytest.mark.asyncio
async def test_handle_user_text_enqueues_via_presence() -> None:
    user = await create_guest_user_for_test(
        nickname_prefix="weixin_pres",
        meta_data={"test": True},
    )
    agent_id = "agent-weixin-inner-tick"
    presence = WeixinInprocessPresence(_binding(agent_id=agent_id))
    mock_agent_presence = MagicMock(spec=AgentChannelPresence)
    mock_agent_presence.handle_user_text = AsyncMock(return_value="")

    with (
        patch(
            "backend.ops.weixin_channel.inprocess_presence._inty_user_from_binding",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.turn_channel_up",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.ensure_presence",
            new_callable=AsyncMock,
            return_value=mock_agent_presence,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.get_presence",
            return_value=mock_agent_presence,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.deps.get_user_from_token",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.agent_service.get_agent_for_chat",
            new_callable=AsyncMock,
            return_value={"id": agent_id},
        ),
    ):
        await presence.start(MagicMock())
        reply = await presence.handle_user_text("hello weixin")

    assert reply == ""
    mock_agent_presence.handle_user_text.assert_awaited_once()
    await _delete_user(user.id)
