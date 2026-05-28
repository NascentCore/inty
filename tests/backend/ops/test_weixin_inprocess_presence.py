"""Weixin in-process presence resolves Inty user from JWT, not demo session_id."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.ops.weixin_channel.inprocess_presence import (
    WeixinInprocessPresence,
    _inty_user_from_binding,
)
from backend.ops.weixin_channel.session import WeixinChannelBinding


def _binding() -> WeixinChannelBinding:
    return WeixinChannelBinding(
        user_id="demo-session-uuid",
        agent_id="agent-1",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt-token",
        weixin_account_id="wx-acct",
        weixin_token="token",
        weixin_base_url="https://ilinkai.weixin.qq.com",
    )


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
    with patch(
        "backend.ops.weixin_channel.inprocess_presence.deps.get_user_from_token",
        new_callable=AsyncMock,
        return_value=None,
    ):
        reply = await presence.handle_user_text("hello")
    assert "JWT" in reply or "token" in reply.lower()
