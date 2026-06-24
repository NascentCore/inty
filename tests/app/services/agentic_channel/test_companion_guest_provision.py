"""Tests for companion production guest user + agent provisioning helpers."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.companion_bond import CompanionBond, CompanionBondState
from app.models.user import AuthType, Gender, User
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    PrivateAgentInput,
    ProvisionGuestScopeInput,
    add_guest_user,
    add_private_agent,
    guest_nickname,
    provision_guest_scope,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    assert_companion_guest_agent_leaves_legacy_character_fields_null,
    assert_companion_guest_identity_has_no_readable_id,
)


@pytest.mark.asyncio
async def test_add_guest_user_sets_nickname_and_meta_data() -> None:
    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix="Probe",
                meta_data={"probe": True},
            ),
        )
        await db.commit()
        assert user.auth_type == AuthType.GUEST
        assert user.meta_data == {"probe": True}
        assert user.nickname == guest_nickname(
            prefix="Probe",
            user_id=user.id,
        )
        assert_companion_guest_identity_has_no_readable_id(user=user)
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


@pytest.mark.asyncio
async def test_add_private_agent_normalizes_gender() -> None:
    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix="gender",
                meta_data={"test": True},
            ),
        )
        await db.flush()
        male_agent = await add_private_agent(
            db,
            PrivateAgentInput(
                user_id=user.id,
                name=f"gender-agent-{uuid.uuid4().hex[:8]}",
                gender="MALE",
            ),
        )
        other_agent = await add_private_agent(
            db,
            PrivateAgentInput(
                user_id=user.id,
                name=f"gender-agent-{uuid.uuid4().hex[:8]}",
                gender="NON_BINARY",
            ),
        )
        await db.commit()
        assert male_agent.gender == Gender.MALE
        assert other_agent.gender == Gender.OTHER
        assert_companion_guest_identity_has_no_readable_id(
            user=user, agent=male_agent
        )
        assert_companion_guest_identity_has_no_readable_id(
            user=user, agent=other_agent
        )
        assert_companion_guest_agent_leaves_legacy_character_fields_null(
            male_agent
        )
        assert_companion_guest_agent_leaves_legacy_character_fields_null(
            other_agent
        )
        await db.execute(
            delete(CompanionBond).where(CompanionBond.user_id == user.id)
        )
        await db.execute(delete(Agent).where(Agent.creator_id == user.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


@pytest.mark.asyncio
async def test_provision_guest_scope_creates_linked_user_and_agent() -> None:
    async with AsyncSessionLocal() as db:
        scope = await provision_guest_scope(
            db,
            ProvisionGuestScopeInput(
                channel=ChannelKind.WECHAT_WEIXIN,
                nickname_prefix="Scope",
                meta_data={"scope": True},
            ),
        )
        await db.commit()
        user_row = await db.execute(
            select(User).where(User.id == scope.user_id)
        )
        user = user_row.scalar_one()
        agent_row = await db.execute(
            select(Agent).where(Agent.id == scope.agent_id)
        )
        agent = agent_row.scalar_one()
        bond_row = await db.execute(
            select(CompanionBond).where(
                CompanionBond.user_id == scope.user_id,
                CompanionBond.agent_id == scope.agent_id,
            )
        )
        bond = bond_row.scalar_one()
        assert user.auth_type == AuthType.GUEST
        assert user.meta_data == {"scope": True}
        assert user.nickname == guest_nickname(prefix="Scope", user_id=user.id)
        assert_companion_guest_identity_has_no_readable_id(
            user=user, agent=agent
        )
        assert agent.creator_id == user.id
        assert agent.name.startswith("weixin-companion-")
        assert bond.state == CompanionBondState.ACTIVE
        assert_companion_guest_agent_leaves_legacy_character_fields_null(agent)
        await db.execute(
            delete(CompanionBond).where(CompanionBond.id == bond.id)
        )
        await db.execute(delete(Agent).where(Agent.id == agent.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()
