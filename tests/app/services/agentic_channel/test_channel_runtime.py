"""Tests for per-scope channel runtime turn up/down."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.user import User
from app.services.agentic_channel.adapters.weixin import WeixinChannelAdapterStub
from app.services.agentic_channel.channel_runtime import (
    ChannelRuntimeState,
    clear_registries_for_tests,
    get_scope_channel_registry,
    turn_channel_down,
    turn_channel_up,
)
from app.services.agentic_channel.endpoints import bind_endpoint
from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
)


async def _create_scope() -> AgentScope:
    return await create_guest_scope_for_test(
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
        nickname_prefix="runtime",
        meta_data={"test": True},
    )


async def _cleanup_scope(scope: AgentScope) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgentChannelEndpoint).where(
                AgentChannelEndpoint.user_id == scope.user_id
            )
        )
        await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
        await db.execute(delete(User).where(User.id == scope.user_id))
        await db.commit()


@pytest.fixture(autouse=True)
async def _clear_channel_registries() -> None:
    yield
    clear_registries_for_tests()


@pytest.mark.asyncio
async def test_turn_up_supersedes_prior_active_channel() -> None:
    scope = await _create_scope()
    try:
        await bind_endpoint(
            scope,
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=f"tg-1-{uuid.uuid4().hex}",
            channel_user_id=f"tu-1-{uuid.uuid4().hex}",
        )
        await bind_endpoint(
            scope,
            channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
            channel_address=f"wx-peer-{uuid.uuid4().hex}",
            channel_user_id=f"wx-user-{uuid.uuid4().hex}",
        )
        registry = get_scope_channel_registry(scope)
        from app.external_services.telegram_bot_api import TelegramBotApi
        from app.services.agentic_channel.adapters.telegram import (
            TelegramChannelAdapter,
        )

        tg_adapter = TelegramChannelAdapter(
            api=TelegramBotApi(bot_token="test"),
            channel_address="tg-1",
        )
        await turn_channel_up(
            scope,
            CompanionRuntimeChannel.TELEGRAM,
            adapter=tg_adapter,
            reason="test",
        )
        assert registry.active_channel() == CompanionRuntimeChannel.TELEGRAM

        wx_adapter = WeixinChannelAdapterStub()
        await turn_channel_up(
            scope,
            CompanionRuntimeChannel.WECHAT_WEIXIN,
            adapter=wx_adapter,
            reason="test",
        )
        assert registry.active_channel() == CompanionRuntimeChannel.WECHAT_WEIXIN
        assert (
            registry.state_of(CompanionRuntimeChannel.TELEGRAM)
            == ChannelRuntimeState.INACTIVE
        )
    finally:
        await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_turn_down_idempotent() -> None:
    scope = await _create_scope()
    try:
        await bind_endpoint(
            scope,
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=f"tg-2-{uuid.uuid4().hex}",
            channel_user_id=f"tu-2-{uuid.uuid4().hex}",
        )
        registry = get_scope_channel_registry(scope)
        await turn_channel_down(
            scope,
            CompanionRuntimeChannel.TELEGRAM,
            reason="noop",
        )
        assert registry.active_channel() is None
    finally:
        await _cleanup_scope(scope)
