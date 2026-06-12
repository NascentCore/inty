"""Tests for agent_channel endpoint bind/resolve and 1:1 channel_user_id bonding."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal, async_engine
from app.models.agent import Agent, AgentVisibility
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.registry import load_model_modules
from app.models.user import AuthType, User
from app.schemas.agent import AgentCreate
from app.services import agent_service
from app.services.agentic_channel.endpoints import (
    assert_inbound_endpoint_identity,
    bind_endpoint,
    inbound_channel_user_id_matches,
    resolve_scope,
    resolve_scope_by_channel_user_id,
)
from app.services.agentic_channel.errors import ChannelEndpointConflictError
from app.services.user_service import generate_next_readable_id


async def _create_user_and_agent() -> AgentScope:
    async with AsyncSessionLocal() as db:
        user_id = get_new_user_id()
        readable_id = await generate_next_readable_id(db)
        user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.GUEST,
            nickname="endpoint-test",
            meta_data={"test": True},
        )
        db.add(user)
        await db.commit()
        agent = await agent_service.create_agent(
            db,
            agent_in=AgentCreate(
                name="endpoint-agent",
                gender="FEMALE",
                visibility=AgentVisibility.PRIVATE,
                intro="demo",
                opening="hi",
                personality="warm",
                scenario="test",
            ),
            user_id=user_id,
        )
        await db.commit()
        return AgentScope(user_id=user_id, agent_id=agent.id)


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
async def _dispose_engine() -> None:
    load_model_modules()
    await async_engine.dispose()
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_bind_and_resolve_by_address() -> None:
    scope = await _create_user_and_agent()
    address = f"addr-{uuid.uuid4().hex}"
    user_id = f"tg-user-{uuid.uuid4().hex}"
    try:
        record = await bind_endpoint(
            scope,
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=address,
            channel_user_id=user_id,
        )
        assert record.channel_address == address
        resolved = await resolve_scope(
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=address,
        )
        assert resolved == scope
        by_user = await resolve_scope_by_channel_user_id(
            channel=CompanionRuntimeChannel.TELEGRAM,
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
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=f"addr-a-{uuid.uuid4().hex}",
            channel_user_id=shared_user_id,
        )
        with pytest.raises(ChannelEndpointConflictError):
            await bind_endpoint(
                scope_b,
                channel=CompanionRuntimeChannel.TELEGRAM,
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
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=address,
            channel_user_id="111",
        )
        assert await inbound_channel_user_id_matches(
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=address,
            channel_user_id="111",
        )
        assert not await inbound_channel_user_id_matches(
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=address,
            channel_user_id="222",
        )
        with pytest.raises(ChannelEndpointConflictError):
            await assert_inbound_endpoint_identity(
                channel=CompanionRuntimeChannel.TELEGRAM,
                channel_address=address,
                channel_user_id="222",
            )
    finally:
        await _cleanup_scope(scope)
