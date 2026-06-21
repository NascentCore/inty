"""Tests for active companion bond service invariants."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.companion_bond import CompanionBond, CompanionBondState
from app.models.user import User
from app.services.agentic_channel.companion_bonds import (
    active_companion_scope_for_user,
    create_active_companion_bond,
    deactivate_companion_bond,
    get_companion_bond_for_scope,
    has_active_companion_bond,
    has_active_companion_bond_for_agent,
    list_active_companion_agent_scope_keys,
    pause_companion_bond_runtime,
    require_active_companion_bond,
    resume_companion_bond_runtime,
)
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    add_companion_guest_agent_for_user,
    add_guest_user,
)
from app.services.agentic_channel.errors import CompanionBondInvariantError


async def _create_unbonded_scope(
    db: AsyncSession,
) -> AgentScope:
    user = await add_guest_user(
        db,
        GuestUserInput(
            nickname_prefix="Bond",
            meta_data={"test": True},
        ),
    )
    agent = await add_companion_guest_agent_for_user(
        db,
        user_id=user.id,
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
    )
    return AgentScope(user_id=user.id, agent_id=agent.id)


async def _delete_scope(db: AsyncSession, scope: AgentScope) -> None:
    await db.execute(
        delete(CompanionBond).where(CompanionBond.user_id == scope.user_id)
    )
    await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
    await db.execute(delete(User).where(User.id == scope.user_id))


@pytest.mark.asyncio
async def test_create_and_require_active_companion_bond() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        bond = await create_active_companion_bond(db, scope)
        await db.commit()
        assert bond.user_id == scope.user_id
        assert bond.agent_id == scope.agent_id
        assert bond.state == CompanionBondState.ACTIVE

        required = await require_active_companion_bond(db, scope)
        resolved = await active_companion_scope_for_user(db, scope.user_id)
        assert required.id == bond.id
        assert resolved == scope
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_create_active_companion_bond_rejects_duplicate_user() -> None:
    async with AsyncSessionLocal() as db:
        first = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, first)
        second_agent = await add_companion_guest_agent_for_user(
            db,
            user_id=first.user_id,
            kind=CompanionGuestAgentKind.TELEGRAM,
        )
        second = AgentScope(user_id=first.user_id, agent_id=second_agent.id)
        with pytest.raises(CompanionBondInvariantError):
            await create_active_companion_bond(db, second)
        await db.rollback()
        await _delete_scope(db, first)
        await db.commit()


@pytest.mark.asyncio
async def test_require_active_companion_bond_rejects_zero_and_multiple() -> (
    None
):
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        with pytest.raises(CompanionBondInvariantError):
            await require_active_companion_bond(db, scope)

        for _ in range(2):
            db.add(
                CompanionBond(
                    id=str(uuid.uuid4()),
                    user_id=scope.user_id,
                    agent_id=scope.agent_id,
                    state=CompanionBondState.ACTIVE,
                )
            )
        await db.flush()
        with pytest.raises(CompanionBondInvariantError):
            await require_active_companion_bond(db, scope)
        await db.rollback()
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_require_active_companion_bond_rejects_deleted_rows() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        agent_row = await db.execute(
            select(Agent).where(Agent.id == scope.agent_id)
        )
        agent = agent_row.scalar_one()
        agent.deleted_at = datetime.now(UTC)
        await db.flush()

        with pytest.raises(CompanionBondInvariantError):
            await require_active_companion_bond(db, scope)
        await db.rollback()
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_deactivate_companion_bond_marks_inactive() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        await db.commit()

        bond = await deactivate_companion_bond(db, scope)
        assert bond.state == CompanionBondState.INACTIVE
        assert bond.inactive_at is not None
        assert not await has_active_companion_bond(db, scope)
        with pytest.raises(CompanionBondInvariantError):
            await require_active_companion_bond(db, scope)
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_pause_and_resume_companion_bond_runtime() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        await db.commit()

        changed = await pause_companion_bond_runtime(db, scope)
        assert changed is True
        bond = await require_active_companion_bond(db, scope)
        assert bond.state == CompanionBondState.ACTIVE
        assert bond.runtime_paused_at is not None
        await db.commit()

        paused_twice = await pause_companion_bond_runtime(db, scope)
        assert paused_twice is False

        keys = await list_active_companion_agent_scope_keys(db)
        assert (scope.user_id, scope.agent_id) not in keys

        changed = await resume_companion_bond_runtime(db, scope)
        assert changed is True
        assert bond.runtime_paused_at is None
        assert bond.last_resumed_at is not None
        await db.commit()

        keys_after_resume = await list_active_companion_agent_scope_keys(db)
        assert (scope.user_id, scope.agent_id) in keys_after_resume

        changed_again = await resume_companion_bond_runtime(db, scope)
        assert changed_again is False
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_get_companion_bond_for_scope_returns_exact_unique_bond() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        bond = await create_active_companion_bond(db, scope)
        await db.commit()

        found = await get_companion_bond_for_scope(db, scope)
        assert found is not None
        assert found.id == bond.id

        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_has_active_companion_bond_fails_closed_on_conflict() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        second_agent = await add_companion_guest_agent_for_user(
            db,
            user_id=scope.user_id,
            kind=CompanionGuestAgentKind.TELEGRAM,
        )
        db.add(
            CompanionBond(
                id=str(uuid.uuid4()),
                user_id=scope.user_id,
                agent_id=second_agent.id,
                state=CompanionBondState.ACTIVE,
            )
        )
        await db.flush()

        assert not await has_active_companion_bond(db, scope)
        assert not await has_active_companion_bond_for_agent(db, scope.agent_id)
        await db.rollback()
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_list_active_companion_agent_scope_keys() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        await db.commit()
        keys = await list_active_companion_agent_scope_keys(db)
        assert (scope.user_id, scope.agent_id) in keys
        await deactivate_companion_bond(db, scope)
        await db.commit()
        keys_after = await list_active_companion_agent_scope_keys(db)
        assert (scope.user_id, scope.agent_id) not in keys_after
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_list_active_companion_agent_scope_keys_skips_conflicts() -> None:
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        second_agent = await add_companion_guest_agent_for_user(
            db,
            user_id=scope.user_id,
            kind=CompanionGuestAgentKind.TELEGRAM,
        )
        second = AgentScope(user_id=scope.user_id, agent_id=second_agent.id)
        db.add(
            CompanionBond(
                id=str(uuid.uuid4()),
                user_id=second.user_id,
                agent_id=second.agent_id,
                state=CompanionBondState.ACTIVE,
            )
        )
        await db.flush()

        keys = await list_active_companion_agent_scope_keys(db)
        assert (scope.user_id, scope.agent_id) not in keys
        assert (second.user_id, second.agent_id) not in keys
        await db.rollback()
        await _delete_scope(db, scope)
        await db.commit()


@pytest.mark.asyncio
async def test_list_active_companion_agent_scope_keys_skips_deleted_rows() -> (
    None
):
    async with AsyncSessionLocal() as db:
        scope = await _create_unbonded_scope(db)
        await create_active_companion_bond(db, scope)
        agent_row = await db.execute(
            select(Agent).where(Agent.id == scope.agent_id)
        )
        agent = agent_row.scalar_one()
        agent.deleted_at = datetime.now(UTC)
        await db.flush()

        keys = await list_active_companion_agent_scope_keys(db)
        assert (scope.user_id, scope.agent_id) not in keys
        await db.rollback()
        await _delete_scope(db, scope)
        await db.commit()
