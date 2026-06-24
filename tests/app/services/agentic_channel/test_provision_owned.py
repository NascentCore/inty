"""Tests for owned-scope channel provision (AppWS / REPL)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.channel_kind import ChannelKind
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.channel_kind import ChannelKind
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond, CompanionBondState
from app.models.user import User
from app.services.agentic_channel.companion_bonds import (
    deactivate_companion_bond,
)
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    add_companion_guest_agent_for_user,
    add_guest_user,
)
from app.services.agentic_channel.errors import (
    ChannelEndpointConflictError,
    CompanionBondInvariantError,
)
from app.services.agentic_channel.endpoints import upsert_endpoint_in_session
from app.services.agentic_channel.provision import (
    OwnedChannelProvisionInput,
    provision_owned_agent_for_channel,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
)


async def _create_unbonded_scope() -> AgentScope:
    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix="Owned",
                meta_data={"test": True},
            ),
        )
        agent = await add_companion_guest_agent_for_user(
            db,
            user_id=user.id,
            channel=ChannelKind.APP_WS,
        )
        await db.commit()
        return AgentScope(user_id=user.id, agent_id=agent.id)


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
async def test_provision_owned_creates_bond_endpoint_and_memory() -> None:
    scope = await _create_unbonded_scope()
    address = scope.registry_key()
    result = await provision_owned_agent_for_channel(
        input=OwnedChannelProvisionInput(
            channel=ChannelKind.APP_WS,
            channel_address=address,
            channel_user_id=scope.user_id,
            scope=scope,
        ),
    )
    assert result.is_new_user is False
    assert result.scope == scope
    async with AsyncSessionLocal() as db:
        bond_row = await db.execute(
            select(CompanionBond).where(
                CompanionBond.user_id == scope.user_id,
                CompanionBond.agent_id == scope.agent_id,
            )
        )
        bond = bond_row.scalar_one()
        assert bond.state == CompanionBondState.ACTIVE
        endpoint_row = await db.execute(
            select(AgentChannelEndpoint).where(
                AgentChannelEndpoint.channel == ChannelKind.APP_WS.value,
                AgentChannelEndpoint.channel_address == address,
            )
        )
        endpoint = endpoint_row.scalar_one()
        assert endpoint.user_id == scope.user_id
        assert endpoint.agent_id == scope.agent_id
    await _cleanup_user(scope.user_id)


@pytest.mark.asyncio
async def test_provision_owned_idempotent_second_call() -> None:
    scope = await _create_unbonded_scope()
    address = scope.registry_key()
    owned_input = OwnedChannelProvisionInput(
        channel=ChannelKind.APP_WS,
        channel_address=address,
        channel_user_id=scope.user_id,
        scope=scope,
    )
    first = await provision_owned_agent_for_channel(input=owned_input)
    second = await provision_owned_agent_for_channel(input=owned_input)
    assert first.scope == second.scope
    async with AsyncSessionLocal() as db:
        bond_rows = await db.execute(
            select(CompanionBond).where(CompanionBond.user_id == scope.user_id)
        )
        assert len(bond_rows.scalars().all()) == 1
    await _cleanup_user(scope.user_id)


@pytest.mark.asyncio
async def test_provision_owned_rebinds_stale_endpoint_for_same_user() -> None:
    first_scope = await _create_unbonded_scope()
    first_address = first_scope.registry_key()
    await provision_owned_agent_for_channel(
        input=OwnedChannelProvisionInput(
            channel=ChannelKind.APP_WS,
            channel_address=first_address,
            channel_user_id=first_scope.user_id,
            scope=first_scope,
        ),
    )
    async with AsyncSessionLocal() as db:
        await deactivate_companion_bond(db, first_scope)
        second_agent = await add_companion_guest_agent_for_user(
            db,
            user_id=first_scope.user_id,
            channel=ChannelKind.APP_WS,
        )
        await db.commit()
    second_scope = AgentScope(
        user_id=first_scope.user_id,
        agent_id=second_agent.id,
    )
    result = await provision_owned_agent_for_channel(
        input=OwnedChannelProvisionInput(
            channel=ChannelKind.APP_WS,
            channel_address=second_scope.registry_key(),
            channel_user_id=second_scope.user_id,
            scope=second_scope,
        ),
    )
    assert result.scope == second_scope
    async with AsyncSessionLocal() as db:
        endpoint_row = await db.execute(
            select(AgentChannelEndpoint).where(
                AgentChannelEndpoint.channel == ChannelKind.APP_WS.value,
                AgentChannelEndpoint.channel_user_id == first_scope.user_id,
            )
        )
        endpoint = endpoint_row.scalar_one()
        assert endpoint.agent_id == second_scope.agent_id
        assert endpoint.channel_address == second_scope.registry_key()
    await _cleanup_user(first_scope.user_id)


@pytest.mark.asyncio
async def test_provision_owned_rejects_bond_conflict() -> None:
    first_scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="First",
        meta_data={"test": True},
    )
    async with AsyncSessionLocal() as db:
        second_agent = await add_companion_guest_agent_for_user(
            db,
            user_id=first_scope.user_id,
            channel=ChannelKind.APP_WS,
        )
        await db.commit()
    second_scope = AgentScope(
        user_id=first_scope.user_id,
        agent_id=second_agent.id,
    )
    with pytest.raises(CompanionBondInvariantError):
        await provision_owned_agent_for_channel(
            input=OwnedChannelProvisionInput(
                channel=ChannelKind.APP_WS,
                channel_address=second_scope.registry_key(),
                channel_user_id=second_scope.user_id,
                scope=second_scope,
            ),
        )
    await _cleanup_user(first_scope.user_id)


@pytest.mark.asyncio
async def test_provision_owned_rejects_endpoint_scope_mismatch() -> None:
    first = await create_guest_scope_for_test(
        channel=ChannelKind.TELEGRAM,
        nickname_prefix="First",
        meta_data={"test": True},
    )
    second = await create_guest_scope_for_test(
        channel=ChannelKind.TELEGRAM,
        nickname_prefix="Second",
        meta_data={"test": True},
    )
    address = f"tg-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    async with AsyncSessionLocal() as db:
        await upsert_endpoint_in_session(
            db,
            first,
            channel=ChannelKind.TELEGRAM,
            channel_address=address,
            channel_user_id=channel_user_id,
        )
        await db.commit()
    with pytest.raises(ChannelEndpointConflictError):
        await provision_owned_agent_for_channel(
            input=OwnedChannelProvisionInput(
                channel=ChannelKind.TELEGRAM,
                channel_address=address,
                channel_user_id=channel_user_id,
                scope=second,
            ),
        )
    await _cleanup_user(first.user_id)
    await _cleanup_user(second.user_id)
