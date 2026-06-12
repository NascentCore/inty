"""Guest user + chat row provisioning for telegram-demo ``/start``."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent, AgentVisibility
from app.models.user import AuthType, User
from app.schemas.agent import AgentCreate
from app.services import agent_service, chat_service
from app.services.user_service import generate_next_readable_id


@dataclass(frozen=True)
class TelegramProvisionResult:
    user_id: str
    agent_id: str
    chat_id: str
    is_new_user: bool


def _default_agent_create(*, tag: str) -> AgentCreate:
    return AgentCreate(
        name=f"telegram-companion-{tag}",
        gender="FEMALE",
        visibility=AgentVisibility.PRIVATE,
        intro="Telegram demo companion.",
        opening="Hello.",
        personality="Warm, curious.",
        scenario="Telegram chat companion.",
    )


async def _user_by_telegram_chat_id(
    db: AsyncSession,
    telegram_chat_id: str,
) -> User | None:
    assert telegram_chat_id != ""
    stmt = select(User).where(
        User.deleted_at.is_(None),
        User.meta_data["telegram_chat_id"].as_string() == telegram_chat_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _create_telegram_guest_user(
    db: AsyncSession,
    telegram_chat_id: str,
) -> User:
    assert telegram_chat_id != ""
    user_id = get_new_user_id()
    readable_id = await generate_next_readable_id(db)
    suffix = user_id[-8:]
    user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.GUEST,
        nickname=f"Telegram_{suffix}",
        meta_data={
            "telegram_chat_id": telegram_chat_id,
            "telegram_demo": True,
        },
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


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


async def provision_inty_for_telegram_onboard(
    *,
    telegram_chat_id: str,
) -> TelegramProvisionResult:
    """Get or create guest user + first PRIVATE agent for team QR onboard."""
    assert telegram_chat_id != ""
    async with AsyncSessionLocal() as db:
        user = await _user_by_telegram_chat_id(db, telegram_chat_id)
        is_new_user = user is None
        if user is None:
            user = await _create_telegram_guest_user(db, telegram_chat_id)

        agent = await _first_private_agent_for_user(db, user.id)
        if agent is None:
            tag = uuid.uuid4().hex[:10]
            agent = await agent_service.create_agent(
                db,
                agent_in=_default_agent_create(tag=tag),
                user_id=user.id,
            )

        chat = await chat_service.get_or_create_chat_by_agent(
            db=db,
            user_id=user.id,
            agent_id=agent.id,
        )
        await db.commit()
        return TelegramProvisionResult(
            user_id=user.id,
            agent_id=agent.id,
            chat_id=chat.id,
            is_new_user=is_new_user,
        )


async def provision_inty_for_telegram_chat(
    *,
    telegram_chat_id: str,
    agent_id: str,
) -> TelegramProvisionResult:
    """Bind one Telegram DM to an existing companion ``agent_id`` (guest user in DB)."""
    assert telegram_chat_id != ""
    assert agent_id != ""
    async with AsyncSessionLocal() as db:
        agent_row = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_row.scalar_one_or_none()
        if agent is None:
            raise ValueError(f"companion agent not found: {agent_id}")

        user = await _user_by_telegram_chat_id(db, telegram_chat_id)
        is_new_user = user is None
        if user is None:
            user = await _create_telegram_guest_user(db, telegram_chat_id)

        chat = await chat_service.get_or_create_chat_by_agent(
            db=db,
            user_id=user.id,
            agent_id=agent_id,
        )
        await db.commit()
        return TelegramProvisionResult(
            user_id=user.id,
            agent_id=agent_id,
            chat_id=chat.id,
            is_new_user=is_new_user,
        )
