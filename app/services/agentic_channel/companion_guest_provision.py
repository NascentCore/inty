"""Shared guest User + PRIVATE Agent creation for companion production onboard.

Uses ``User.id`` and ``Agent.id`` only; legacy ``readable_id`` is not written.
Enforced by ``chat_ws_boundary.companion_surface_readable_id_references``.

TODO(#3358): DB still has unique constraints on ``readable_id`` for legacy HTTP paths;
do not drop until those callers migrate — see issue for Alembic plan.

TODO(companion-bond-invariant): #3491 — harden active companion uniqueness with
database constraints after v1 service-level checks settle.

**Not** ``agent_service.create_agent``: that path is maintenance-mode HTTP only
(readable_id allocation, avatar crop, opening-voice enqueue, subscription limits).
Companion telegram / weixin / agent-channel onboard must stay on this module.

Legacy character-card columns (``intro``, ``scenario``, ``opening``, ``personality``, …)
are left NULL — see #3359.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.core.companion_harness.agent_channel.gateway_traits import (
    guest_agent_name_for_gateway,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.uuid import get_new_user_id
from app.models.agent import Agent, AgentVisibility
from app.models.user import AuthType, User, normalize_gender
from app.services.agentic_channel.companion_bonds import (
    create_active_companion_bond,
)

COMPANION_GUEST_DEFAULT_GENDER = "FEMALE"


@dataclass(frozen=True)
class GuestUserInput:
    """In-session guest user row (caller commits)."""

    nickname_prefix: str
    meta_data: dict


@dataclass(frozen=True)
class PrivateAgentInput:
    """In-session PRIVATE agent row (caller commits)."""

    user_id: str
    name: str
    gender: str


@dataclass(frozen=True)
class ProvisionGuestScopeInput:
    """Guest user + PRIVATE agent pair for companion onboard (caller commits)."""

    gateway: GatewayKind
    nickname_prefix: str
    meta_data: dict


def guest_nickname(*, prefix: str, user_id: str) -> str:
    assert prefix != ""
    assert user_id != ""
    return f"{prefix}_{user_id[-8:]}"


async def add_guest_user(db: AsyncSession, input: GuestUserInput) -> User:
    assert input.nickname_prefix != ""
    user_id = get_new_user_id()
    user = User(
        id=user_id,
        auth_type=AuthType.GUEST,
        nickname=guest_nickname(prefix=input.nickname_prefix, user_id=user_id),
        meta_data=input.meta_data,
    )
    db.add(user)
    return user


async def add_companion_guest_agent_for_user(
    db: AsyncSession,
    *,
    user_id: str,
    gateway: GatewayKind,
) -> Agent:
    """Add PRIVATE companion agent for existing guest user (caller commits)."""
    assert user_id != ""
    tag = uuid.uuid4().hex[:10]
    return await add_private_agent(
        db,
        PrivateAgentInput(
            user_id=user_id,
            name=guest_agent_name_for_gateway(gateway=gateway, tag=tag),
            gender=COMPANION_GUEST_DEFAULT_GENDER,
        ),
    )


async def add_private_agent(
    db: AsyncSession, input: PrivateAgentInput
) -> Agent:
    assert input.user_id != ""
    assert input.name != ""
    assert input.gender != ""
    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id,
        name=input.name,
        gender=normalize_gender(input.gender),
        visibility=AgentVisibility.PRIVATE,
        creator_id=input.user_id,
    )
    db.add(agent)
    return agent


async def provision_guest_scope(
    db: AsyncSession,
    input: ProvisionGuestScopeInput,
) -> AgentScope:
    """Create guest user + PRIVATE agent in one session (caller commits)."""
    assert input.nickname_prefix != ""
    user = await add_guest_user(
        db,
        GuestUserInput(
            nickname_prefix=input.nickname_prefix,
            meta_data=input.meta_data,
        ),
    )
    agent = await add_companion_guest_agent_for_user(
        db,
        user_id=user.id,
        gateway=input.gateway,
    )
    scope = AgentScope(user_id=user.id, agent_id=agent.id)
    await create_active_companion_bond(db, scope)
    return scope
