"""Weixin in-process presence resolves Inty user from JWT, not demo session_id."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.agentic_companion.inner_tick_delivery import (
    inner_tick_delivery_for_weixin,
)
from app.services.agentic_companion.inner_tick_scope import (
    InnerTickFireInput,
    InnerTickModelSource,
    resolve_inner_tick_scope_coords,
)
from app.services.agentic_companion.session import InnerTickCoords
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


def _noop_create_task(coro, **kwargs) -> asyncio.Future[None]:
    coro.close()
    fut: asyncio.Future[None] = asyncio.get_running_loop().create_future()
    fut.set_result(None)
    return fut


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


@pytest.mark.asyncio
async def test_start_stores_agent_scope_inner_tick_coords() -> None:
    presence = WeixinInprocessPresence(_binding())
    fake_user = MagicMock()
    fake_user.id = "user-test"
    mock_session = MagicMock()
    mock_session.start_inner_tick_worker = AsyncMock()

    with (
        patch(
            "backend.ops.weixin_channel.inprocess_presence._inty_user_from_binding",
            new_callable=AsyncMock,
            return_value=fake_user,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.Session.from_coordinator",
            return_value=mock_session,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.asyncio.create_task",
            side_effect=_noop_create_task,
        ),
        patch(
            "app.services.chat_service.get_or_create_chat_by_agent",
            new_callable=AsyncMock,
        ) as mock_get_chat,
    ):
        await presence.start(MagicMock())

    mock_get_chat.assert_not_awaited()
    coords = InnerTickCoords.from_context(
        presence._coordinator.snapshot_inner_tick_coords()
    )
    assert coords is not None
    expected = AgentScope(user_id="user-test", agent_id="agent-1").memory_store_chat_id()
    assert coords.chat_id == expected


@pytest.mark.asyncio
async def test_start_inner_tick_scope_resolves_agent_scope_chat_id() -> None:
    user = await create_guest_user_for_test(
        nickname_prefix="weixin_pres",
        meta_data={"test": True},
    )
    agent_id = "agent-weixin-inner-tick"
    presence = WeixinInprocessPresence(_binding(agent_id=agent_id))
    mock_session = MagicMock()
    mock_session.start_inner_tick_worker = AsyncMock()

    with (
        patch(
            "backend.ops.weixin_channel.inprocess_presence._inty_user_from_binding",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.Session.from_coordinator",
            return_value=mock_session,
        ),
        patch(
            "backend.ops.weixin_channel.inprocess_presence.asyncio.create_task",
            side_effect=_noop_create_task,
        ),
    ):
        await presence.start(MagicMock())

    coords = InnerTickCoords.from_context(
        presence._coordinator.snapshot_inner_tick_coords()
    )
    assert coords is not None

    async def _noop_text(_text: str) -> None:
        return None

    fire_input = InnerTickFireInput(
        delivery=inner_tick_delivery_for_weixin(_noop_text),
        coords=coords,
        coordinator=presence._coordinator,
        ws_conn_id="test_poll",
        tc_box=[None],
    )
    resolved = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    assert resolved is not None
    assert resolved.chat_row_id == AgentScope(
        user_id=user.id,
        agent_id=agent_id,
    ).memory_store_chat_id()
    assert resolved.chat_row_agent_id == agent_id
    await _delete_user(user.id)
