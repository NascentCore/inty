"""Provision Inty user, agent, and bridge JWT after Weixin iLink QR confirm.

Identity uses ``User.id`` and ``Agent.id`` only; legacy ``readable_id`` is unused.
Enforced by ``chat_ws_boundary.companion_surface_readable_id_references``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.user import User
from app.services.agentic_channel.companion_guest_provision import (
    CompanionGuestAgentKind,
    GuestUserInput,
    PrivateAgentInput,
    add_guest_user,
    add_private_agent,
    companion_guest_agent_create,
    first_private_agent_for_user,
)


@dataclass(frozen=True)
class ProvisionResult:
    """Inty credentials for Weixin bridge binding (JWT is Ops-internal only)."""

    user_id: str
    agent_id: str
    jwt: str
    is_new_user: bool


async def _user_by_ilink_user_id(
    db: AsyncSession,
    ilink_user_id: str,
) -> User | None:
    assert ilink_user_id != ""
    stmt = select(User).where(
        User.deleted_at.is_(None),
        User.meta_data["ilink_user_id"].as_string() == ilink_user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _create_weixin_user(
    db: AsyncSession,
    ilink_user_id: str,
) -> User:
    assert ilink_user_id != ""
    user = await add_guest_user(
        db,
        GuestUserInput(
            nickname_prefix="Weixin",
            meta_data={"ilink_user_id": ilink_user_id},
        ),
    )
    await db.commit()
    await db.refresh(user)
    return user


async def _create_weixin_agent(
    db: AsyncSession,
    *,
    user_id: str,
    tag: str,
) -> Agent:
    assert user_id != ""
    assert tag != ""
    agent = await add_private_agent(
        db,
        PrivateAgentInput(
            user_id=user_id,
            agent_in=companion_guest_agent_create(
                kind=CompanionGuestAgentKind.WEIXIN,
                tag=tag,
            ),
        ),
    )
    await db.commit()
    await db.refresh(agent)
    return agent


async def provision_inty_for_ilink_user(
    *, ilink_user_id: str
) -> ProvisionResult:
    """Get or create Inty user + PRIVATE agent; mint JWT for bridge binding."""
    assert ilink_user_id != ""
    async with AsyncSessionLocal() as db:
        user = await _user_by_ilink_user_id(db, ilink_user_id)
        is_new_user = user is None
        if user is None:
            user = await _create_weixin_user(db, ilink_user_id)

        agent = await first_private_agent_for_user(db, user.id)
        if agent is None:
            tag = uuid.uuid4().hex[:10]
            agent = await _create_weixin_agent(db, user_id=user.id, tag=tag)

        jwt = create_access_token(user.id)
        return ProvisionResult(
            user_id=user.id,
            agent_id=agent.id,
            jwt=jwt,
            is_new_user=is_new_user,
        )
