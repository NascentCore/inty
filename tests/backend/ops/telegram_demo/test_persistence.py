"""Tests for agent_channel endpoint persistence via service layer."""

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
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.endpoints import (
    bind_endpoint,
    list_endpoints_for_channel,
)
from app.services.agentic_channel.provision import provision_agent_for_channel_onboard


@pytest.mark.asyncio
async def test_provision_persists_endpoint_row() -> None:
    telegram_chat_id = f"tg-persist-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    provision = await provision_agent_for_channel_onboard(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    rows = await list_endpoints_for_channel(
        channel=CompanionRuntimeChannel.TELEGRAM
    )
    match = [r for r in rows if r.channel_address == telegram_chat_id]
    assert len(match) == 1
    assert match[0].channel_user_id == channel_user_id
    assert match[0].user_id == provision.scope.user_id

    scope = AgentScope(
        user_id=provision.scope.user_id,
        agent_id=provision.scope.agent_id,
    )
    await bind_endpoint(
        scope,
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    rows = await list_endpoints_for_channel(
        channel=CompanionRuntimeChannel.TELEGRAM
    )
    match = [r for r in rows if r.channel_address == telegram_chat_id]
    assert len(match) == 1

    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgentChannelEndpoint).where(
                AgentChannelEndpoint.user_id == provision.scope.user_id
            )
        )
        await db.execute(
            delete(CompanionBond).where(
                CompanionBond.user_id == provision.scope.user_id
            )
        )
        await db.execute(
            delete(Agent).where(Agent.creator_id == provision.scope.user_id)
        )
        await db.execute(
            delete(User).where(User.id == provision.scope.user_id)
        )
        await db.commit()
