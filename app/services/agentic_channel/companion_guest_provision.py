"""Shared guest User + PRIVATE Agent creation for companion production onboard.

Uses ``User.id`` and ``Agent.id`` only; legacy ``readable_id`` is not written.
Enforced by ``chat_ws_boundary.companion_surface_readable_id_references``.

TODO(#3358): DB still has unique constraints on ``readable_id`` for legacy HTTP paths;
do not drop until those callers migrate — see issue for Alembic plan.

TODO(companion-bond-invariant): #3491 — replace oldest-PRIVATE-agent reuse with
a DB-enforced active companion bond; merge-deselected companions must enter
SEALED state, and replacement/revival must wait for the product reset decision
drafted in docs/companion_harness/CROSS_CHANNEL_IDENTITY_FOLLOWUPS.md.

**Not** ``agent_service.create_agent``: that path is maintenance-mode HTTP only
(readable_id allocation, avatar crop, opening-voice enqueue, subscription limits).
Companion telegram / weixin / agent-channel onboard must stay on this module.

Legacy character-card columns (``intro``, ``scenario``, ``opening``, ``personality``, …)
are left NULL — see #3359.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.uuid import get_new_user_id
from app.models.agent import Agent, AgentVisibility
from app.models.user import AuthType, User, normalize_gender

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

    kind: CompanionGuestAgentKind
    nickname_prefix: str
    meta_data: dict


def guest_nickname(*, prefix: str, user_id: str) -> str:
    assert prefix != ""
    assert user_id != ""
    return f"{prefix}_{user_id[-8:]}"


def companion_guest_agent_name(
    *, kind: CompanionGuestAgentKind, tag: str
) -> str:
    """Channel-specific display name only; legacy character-card fields stay NULL."""
    assert tag != ""
    match kind:
        case CompanionGuestAgentKind.AGENT_CHANNEL:
            return f"agent-channel-{tag}"
        case CompanionGuestAgentKind.TELEGRAM:
            return f"telegram-{tag}"
        case CompanionGuestAgentKind.WEIXIN:
            return f"weixin-companion-{tag}"


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
    kind: CompanionGuestAgentKind,
) -> Agent:
    """Add PRIVATE companion agent for existing guest user (caller commits)."""
    assert user_id != ""
    tag = uuid.uuid4().hex[:10]
    return await add_private_agent(
        db,
        PrivateAgentInput(
            user_id=user_id,
            name=companion_guest_agent_name(kind=kind, tag=tag),
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
        kind=input.kind,
    )
    return AgentScope(user_id=user.id, agent_id=agent.id)


async def first_private_agent_for_user(
    db: AsyncSession,
    user_id: str,
) -> Agent | None:
    """Return oldest PRIVATE agent for user (1:1 companion onboard assumption)."""
    assert user_id != ""
    stmt = (
        select(Agent)
        .where(
            Agent.creator_id == user_id,
            Agent.visibility == AgentVisibility.PRIVATE,
        )
        .order_by(Agent.created_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
