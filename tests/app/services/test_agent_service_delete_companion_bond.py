"""Tests for delete_agent cascading companion bond deactivation."""

from __future__ import annotations


import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agent_service import delete_agent
from app.services.agentic_channel.companion_bonds import (
    create_active_companion_bond,
    ensure_active_companion_bond_for_owned_scope,
    has_active_companion_bond,
)
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    add_companion_guest_agent_for_user,
    add_guest_user,
)


async def _create_unbonded_scope(db):
    user = await add_guest_user(
        db,
        GuestUserInput(
            nickname_prefix="DeleteBond",
            meta_data={"test": True},
        ),
    )
    agent = await add_companion_guest_agent_for_user(
        db,
        user_id=user.id,
        channel=ChannelKind.APP_WS,
    )
    return AgentScope(user_id=user.id, agent_id=agent.id)


async def _delete_scope(db, scope: AgentScope) -> None:
    await db.execute(
        delete(CompanionBond).where(CompanionBond.user_id == scope.user_id)
    )
    await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
    await db.execute(delete(User).where(User.id == scope.user_id))


@pytest.mark.asyncio
async def test_delete_agent_deactivates_active_companion_bond() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        await db.commit()

        agent_row = await db.execute(
            select(Agent).where(Agent.id == scope.agent_id)
        )
        agent = agent_row.scalar_one()
        await delete_agent(db, agent)
        assert not await has_active_companion_bond(db, scope)
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_delete_agent_allows_new_companion_bond_for_same_user() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        await db.commit()

        agent_row = await db.execute(
            select(Agent).where(Agent.id == scope.agent_id)
        )
        agent = agent_row.scalar_one()
        await delete_agent(db, agent)

        second_agent = await add_companion_guest_agent_for_user(
            db,
            user_id=scope.user_id,
            channel=ChannelKind.APP_WS,
        )
        second_scope = AgentScope(
            user_id=scope.user_id, agent_id=second_agent.id
        )
        bond = await ensure_active_companion_bond_for_owned_scope(
            db, second_scope
        )
        assert bond.state.value == "ACTIVE"
        await db.commit()

        await db.execute(delete(Agent).where(Agent.id == second_agent.id))
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_delete_agent_without_bond_succeeds() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await db.commit()

        agent_row = await db.execute(
            select(Agent).where(Agent.id == scope.agent_id)
        )
        agent = agent_row.scalar_one()
        deleted = await delete_agent(db, agent)
        assert deleted.deleted_at is not None
        await _delete_scope(db, scope)
        await db.commit()
