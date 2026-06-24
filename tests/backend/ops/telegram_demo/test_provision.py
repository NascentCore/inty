"""Tests for agent-channel guest provisioning."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.errors import (
    ChannelEndpointConflictError,
    CompanionBondInvariantError,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.services.agentic_channel.provision import (
    OwnedChannelProvisionInput,
    provision_agent_for_channel_onboard,
    provision_owned_agent_for_channel,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    assert_companion_guest_identity_has_no_readable_id,
    create_guest_scope_for_test,
)


async def _create_creator_scope() -> AgentScope:
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.TELEGRAM,
        nickname_prefix="Creator",
        meta_data={"test": True},
    )
    return scope


async def _cleanup_user(user_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgentChannelEndpoint).where(
                AgentChannelEndpoint.user_id == user_id
            )
        )
        await db.execute(
            delete(CompanionBond).where(CompanionBond.user_id == user_id)
        )
        await db.execute(delete(Agent).where(Agent.creator_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_provision_onboard_idempotent() -> None:
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    first = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    assert first.is_new_user is True
    second = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    assert second.is_new_user is False
    assert second.scope == first.scope
    await _cleanup_user(first.scope.user_id)


@pytest.mark.asyncio
async def test_provision_existing_agent_binds_bonded_scope() -> None:
    creator_scope = await _create_creator_scope()
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    first = await provision_owned_agent_for_channel(
        input=OwnedChannelProvisionInput(
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id=channel_user_id,
            scope=creator_scope,
        ),
    )
    assert first.is_new_user is False
    assert first.scope == creator_scope
    async with AsyncSessionLocal() as db:
        row = await db.execute(
            select(User).where(User.id == first.scope.user_id)
        )
        user = row.scalar_one()
        assert user.meta_data == {"test": True}
    await _cleanup_user(first.scope.user_id)


@pytest.mark.asyncio
async def test_provision_onboard_rejects_channel_user_id_mismatch() -> None:
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    first = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    with pytest.raises(ChannelEndpointConflictError):
        await provision_agent_for_channel_onboard(
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id=f"other-{uuid.uuid4().hex}",
        )
    await _cleanup_user(first.scope.user_id)


@pytest.mark.asyncio
async def test_telegram_onboard_leaves_readable_id_unset() -> None:
    """Telegram onboard must not write legacy readable_id (nullable ORM column)."""
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    result = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    assert result.is_new_user is True
    async with AsyncSessionLocal() as db:
        user_row = await db.execute(
            select(User).where(User.id == result.scope.user_id)
        )
        user = user_row.scalar_one()
        agent_row = await db.execute(
            select(Agent).where(Agent.id == result.scope.agent_id)
        )
        agent = agent_row.scalar_one()
        assert_companion_guest_identity_has_no_readable_id(
            user=user, agent=agent
        )
    await _cleanup_user(result.scope.user_id)


@pytest.mark.asyncio
async def test_concurrent_provision_single_endpoint_no_orphan_users() -> None:
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    results = await asyncio.gather(
        provision_agent_for_channel_onboard(
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id=channel_user_id,
        ),
        provision_agent_for_channel_onboard(
            channel=ChannelKind.TELEGRAM,
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
        bond_rows = await db.execute(
            select(CompanionBond).where(
                CompanionBond.user_id == results[0].scope.user_id
            )
        )
        bonds = bond_rows.scalars().all()
        assert len(bonds) == 1
    await _cleanup_user(results[0].scope.user_id)


@pytest.mark.asyncio
async def test_provision_existing_endpoint_requires_active_bond() -> None:
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    first = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(CompanionBond).where(
                CompanionBond.user_id == first.scope.user_id
            )
        )
        await db.commit()
    with pytest.raises(CompanionBondInvariantError):
        await provision_agent_for_channel_onboard(
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id=channel_user_id,
        )
    await _cleanup_user(first.scope.user_id)


@pytest.mark.asyncio
async def test_provision_existing_endpoint_rejects_bond_mismatch() -> None:
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    first = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=address,
        channel_user_id=channel_user_id,
    )
    other = await create_guest_scope_for_test(
        channel=ChannelKind.TELEGRAM,
        nickname_prefix="Other",
        meta_data={"test": True},
    )
    async with AsyncSessionLocal() as db:
        bond_row = await db.execute(
            select(CompanionBond).where(
                CompanionBond.user_id == first.scope.user_id
            )
        )
        bond = bond_row.scalar_one()
        bond.agent_id = other.agent_id
        await db.commit()
    with pytest.raises(CompanionBondInvariantError):
        await provision_agent_for_channel_onboard(
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id=channel_user_id,
        )
    await _cleanup_user(first.scope.user_id)
    await _cleanup_user(other.user_id)
