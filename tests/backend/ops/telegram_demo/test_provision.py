"""Tests for agent-channel guest provisioning."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal, async_engine
from app.models.agent import Agent, AgentVisibility
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.registry import load_model_modules
from app.models.user import AuthType, User
from app.schemas.agent import AgentCreate
from app.services import agent_service
from app.services.agentic_channel.errors import ChannelEndpointConflictError
from app.services.agentic_channel.provision import (
    provision_agent_for_channel_onboard,
    provision_agent_for_existing_agent,
)
from app.services.user_service import generate_next_readable_id


async def _create_creator_agent() -> str:
    async with AsyncSessionLocal() as db:
        user_id = get_new_user_id()
        readable_id = await generate_next_readable_id(db)
        user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.GUEST,
            nickname="Creator",
            meta_data={"test": True},
        )
        db.add(user)
        await db.commit()
        agent = await agent_service.create_agent(
            db,
            agent_in=AgentCreate(
                name="telegram-demo-agent",
                gender="FEMALE",
                visibility=AgentVisibility.PRIVATE,
                intro="demo",
                opening="hi",
                personality="warm",
                scenario="telegram",
            ),
            user_id=user_id,
        )
        await db.commit()
        return agent.id


async def _cleanup_user(user_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgentChannelEndpoint).where(
                AgentChannelEndpoint.user_id == user_id
            )
        )
        await db.execute(delete(Agent).where(Agent.creator_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.fixture(autouse=True)
async def _dispose_engine() -> None:
    load_model_modules()
    await async_engine.dispose()
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_provision_onboard_idempotent() -> None:
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    first = await provision_agent_for_channel_onboard(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    assert first.is_new_user is True
    second = await provision_agent_for_channel_onboard(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    assert second.is_new_user is False
    assert second.scope == first.scope
    await _cleanup_user(first.scope.user_id)


@pytest.mark.asyncio
async def test_provision_existing_agent_creates_guest() -> None:
    agent_id = await _create_creator_agent()
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    first = await provision_agent_for_existing_agent(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
        agent_id=agent_id,
    )
    assert first.is_new_user is True
    assert first.scope.agent_id == agent_id
    async with AsyncSessionLocal() as db:
        row = await db.execute(select(User).where(User.id == first.scope.user_id))
        user = row.scalar_one()
        assert user.meta_data is not None
        assert user.meta_data.get("agent_channel") is True
    await _cleanup_user(first.scope.user_id)


@pytest.mark.asyncio
async def test_provision_onboard_rejects_channel_user_id_mismatch() -> None:
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    first = await provision_agent_for_channel_onboard(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    with pytest.raises(ChannelEndpointConflictError):
        await provision_agent_for_channel_onboard(
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=address,
            channel_user_id=f"other-{uuid.uuid4().hex}",
        )
    await _cleanup_user(first.scope.user_id)


@pytest.mark.asyncio
async def test_concurrent_provision_single_endpoint_no_orphan_users() -> None:
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    results = await asyncio.gather(
        provision_agent_for_channel_onboard(
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=address,
            channel_user_id=channel_user_id,
        ),
        provision_agent_for_channel_onboard(
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=address,
            channel_user_id=channel_user_id,
        ),
    )
    assert results[0].scope == results[1].scope
    assert sum(1 for r in results if r.is_new_user) == 1
    async with AsyncSessionLocal() as db:
        endpoint_rows = await db.execute(
            select(AgentChannelEndpoint).where(
                AgentChannelEndpoint.channel_address == address
            )
        )
        endpoints = endpoint_rows.scalars().all()
        assert len(endpoints) == 1
        assert endpoints[0].user_id == results[0].scope.user_id
        assert endpoints[0].agent_id == results[0].scope.agent_id
    await _cleanup_user(results[0].scope.user_id)
