"""DB fixtures for agentic_channel tests using companion production identity.

Uses ``provision_guest_scope`` (no ``readable_id``, no ``agent_service.create_agent``
side effects). Maintenance-mode HTTP tests should keep using ``agent_service`` directly.
"""

from __future__ import annotations

from sqlalchemy import delete

from app.core.companion_harness.agent_channel.channel_kind import ChannelKind
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    ProvisionGuestScopeInput,
    add_guest_user,
    provision_guest_scope,
)


async def delete_guest_scope_for_test(scope: AgentScope) -> None:
    """Delete companion guest scope rows created by agentic_channel fixtures."""
    # TODO(companion-test-fixture-cleanup): Replace scattered direct guest-scope
    # cleanup in companion/telegram tests with this helper.
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(CompanionBond).where(CompanionBond.user_id == scope.user_id)
        )
        await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
        await db.execute(delete(User).where(User.id == scope.user_id))
        await db.commit()


def assert_companion_guest_identity_has_no_readable_id(
    *,
    user: User,
    agent: Agent | None = None,
) -> None:
    assert user.readable_id is None
    if agent is not None:
        assert agent.readable_id is None


def assert_companion_guest_agent_leaves_legacy_character_fields_null(
    agent: Agent,
) -> None:
    """Companion production rows must not seed legacy HTTP character-card columns."""
    assert agent.intro is None
    assert agent.opening is None
    assert agent.personality is None
    assert agent.scenario is None


async def create_guest_user_for_test(
    *,
    nickname_prefix: str,
    meta_data: dict,
) -> User:
    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix=nickname_prefix,
                meta_data=meta_data,
            ),
        )
        await db.commit()
        await db.refresh(user)
        return user


async def create_guest_scope_for_test(
    *,
    channel: ChannelKind,
    nickname_prefix: str,
    meta_data: dict,
) -> AgentScope:
    async with AsyncSessionLocal() as db:
        scope = await provision_guest_scope(
            db,
            ProvisionGuestScopeInput(
                channel=channel,
                nickname_prefix=nickname_prefix,
                meta_data=meta_data,
            ),
        )
        await db.commit()
        return scope
