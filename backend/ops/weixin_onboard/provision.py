"""Provision Inty user, agent, and bridge JWT after Weixin iLink QR confirm."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent, AgentVisibility
from app.models.user import AuthType, User
from app.schemas.agent import AgentCreate
from app.services import agent_service
from app.services.user_service import generate_next_readable_id


@dataclass(frozen=True)
class ProvisionResult:
    """Inty credentials for Weixin bridge binding (JWT is Ops-internal only)."""

    user_id: str
    agent_id: str
    jwt: str
    is_new_user: bool


def _default_agent_create(*, tag: str) -> AgentCreate:
    return AgentCreate(
        name=f"weixin-companion-{tag}",
        gender="FEMALE",
        visibility=AgentVisibility.PRIVATE,
        intro="Weixin onboard companion.",
        opening="Hello.",
        personality="Warm, curious.",
        scenario="Weixin chat companion.",
    )


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


async def _first_private_agent_for_user(
    db: AsyncSession,
    user_id: str,
) -> Agent | None:
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


async def _create_weixin_user(
    db: AsyncSession,
    ilink_user_id: str,
) -> User:
    assert ilink_user_id != ""
    user_id = get_new_user_id()
    readable_id = await generate_next_readable_id(db)
    suffix = user_id[-8:]
    user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.GUEST,
        nickname=f"Weixin_{suffix}",
        meta_data={"ilink_user_id": ilink_user_id},
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def provision_inty_for_ilink_user(*, ilink_user_id: str) -> ProvisionResult:
    """Get or create Inty user + PRIVATE agent; mint JWT for bridge binding."""
    assert ilink_user_id != ""
    async with AsyncSessionLocal() as db:
        user = await _user_by_ilink_user_id(db, ilink_user_id)
        is_new_user = user is None
        if user is None:
            user = await _create_weixin_user(db, ilink_user_id)

        agent = await _first_private_agent_for_user(db, user.id)
        if agent is None:
            tag = uuid.uuid4().hex[:10]
            agent = await agent_service.create_agent(
                db,
                agent_in=_default_agent_create(tag=tag),
                user_id=user.id,
            )

        jwt = create_access_token(user.id)
        return ProvisionResult(
            user_id=user.id,
            agent_id=agent.id,
            jwt=jwt,
            is_new_user=is_new_user,
        )
