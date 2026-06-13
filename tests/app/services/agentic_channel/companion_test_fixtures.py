"""DB fixtures for agentic_channel tests using companion production identity.

Uses ``provision_guest_scope`` (no ``readable_id``, no ``agent_service.create_agent``
side effects). Maintenance-mode HTTP tests should keep using ``agent_service`` directly.
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.user import User
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    ProvisionGuestScopeInput,
    add_guest_user,
    provision_guest_scope,
)


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
    kind: CompanionGuestAgentKind,
    nickname_prefix: str,
    meta_data: dict,
) -> AgentScope:
    async with AsyncSessionLocal() as db:
        scope = await provision_guest_scope(
            db,
            ProvisionGuestScopeInput(
                kind=kind,
                nickname_prefix=nickname_prefix,
                meta_data=meta_data,
            ),
        )
        await db.commit()
        return scope
