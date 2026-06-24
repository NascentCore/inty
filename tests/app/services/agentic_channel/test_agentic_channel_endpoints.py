"""Tests for agent_channel endpoint bind/resolve and 1:1 channel_user_id bonding."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.endpoints import (
    assert_inbound_endpoint_identity,
    bind_endpoint,
    inbound_channel_user_id_matches,
    resolve_scope,
    resolve_scope_by_channel_user_id,
)
from app.services.agentic_channel.errors import ChannelEndpointConflictError
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
)


async def _create_user_and_agent() -> AgentScope:
    return await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="endpoint",
        meta_data={"test": True},
    )


async def _cleanup_scope(scope: AgentScope) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgentChannelEndpoint).where(
                AgentChannelEndpoint.user_id == scope.user_id
            )
        )
        await db.execute(
            delete(CompanionBond).where(CompanionBond.user_id == scope.user_id)
        )
        await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
        await db.execute(delete(User).where(User.id == scope.user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_bind_and_resolve_by_address() -> None:
    scope = await _create_user_and_agent()
    address = f"addr-{uuid.uuid4().hex}"
    user_id = f"tg-user-{uuid.uuid4().hex}"
    try:
        record = await bind_endpoint(
            scope,
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id=user_id,
        )
        assert record.channel_address == address
        resolved = await resolve_scope(
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
        )
        assert resolved == scope
        by_user = await resolve_scope_by_channel_user_id(
            channel=ChannelKind.TELEGRAM,
            channel_user_id=user_id,
        )
        assert by_user == scope
    finally:
        await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_channel_user_id_conflict_rejects_second_user() -> None:
    scope_a = await _create_user_and_agent()
    scope_b = await _create_user_and_agent()
    shared_user_id = f"shared-{uuid.uuid4().hex}"
    try:
        await bind_endpoint(
            scope_a,
            channel=ChannelKind.TELEGRAM,
            channel_address=f"addr-a-{uuid.uuid4().hex}",
            channel_user_id=shared_user_id,
        )
        with pytest.raises(ChannelEndpointConflictError):
            await bind_endpoint(
                scope_b,
                channel=ChannelKind.TELEGRAM,
                channel_address=f"addr-b-{uuid.uuid4().hex}",
                channel_user_id=shared_user_id,
            )
    finally:
        await _cleanup_scope(scope_a)
        await _cleanup_scope(scope_b)


@pytest.mark.asyncio
async def test_inbound_channel_user_id_mismatch() -> None:
    scope = await _create_user_and_agent()
    address = f"addr-{uuid.uuid4().hex}"
    try:
        await bind_endpoint(
            scope,
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id="111",
        )
        assert await inbound_channel_user_id_matches(
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id="111",
        )
        assert not await inbound_channel_user_id_matches(
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id="222",
        )
        with pytest.raises(ChannelEndpointConflictError):
            await assert_inbound_endpoint_identity(
                channel=ChannelKind.TELEGRAM,
                channel_address=address,
                channel_user_id="222",
            )
    finally:
        await _cleanup_scope(scope)
