"""Tests for Telegram demo guest user provisioning."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal, async_engine
from app.models.agent import Agent, AgentVisibility
from app.models.chat import Chat
from app.models.registry import load_model_modules
from app.models.user import AuthType, User
from app.schemas.agent import AgentCreate
from app.services import agent_service
from app.services.user_service import generate_next_readable_id
from backend.ops.telegram_demo.provision import (
    provision_inty_for_telegram_chat,
    provision_inty_for_telegram_onboard,
)


async def _create_creator_user(db: AsyncSession) -> str:
    user_id = get_new_user_id()
    readable_id = await generate_next_readable_id(db)
    user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.GUEST,
        nickname="Creator",
        meta_data={"telegram_demo_test": True},
    )
    db.add(user)
    await db.commit()
    return user_id


@pytest.fixture
async def async_db_session():
    load_model_modules()
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
    await engine.dispose()


async def _delete_user_and_agents(db: AsyncSession, user_id: str) -> None:
    await db.execute(delete(Agent).where(Agent.creator_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


@pytest.mark.asyncio
async def test_provision_telegram_guest_reuses_user(async_db_session: AsyncSession) -> None:
    await async_engine.dispose()
    telegram_chat_id = f"tg-{uuid.uuid4().hex}"
    async with AsyncSessionLocal() as db:
        creator_id = await _create_creator_user(db)
        agent = await agent_service.create_agent(
            db,
            agent_in=AgentCreate(
                name="telegram-demo-agent",
                gender="FEMALE",
                visibility=AgentVisibility.PRIVATE,
                intro="demo",
                opening="hi",
                personality="warm",
                scenario="telegram",
            ),
            user_id=creator_id,
        )
        agent_id = agent.id

    first = await provision_inty_for_telegram_chat(
        telegram_chat_id=telegram_chat_id,
        agent_id=agent_id,
    )
    assert first.is_new_user is True
    assert first.agent_id == agent_id
    assert first.chat_id != ""

    row = await async_db_session.execute(
        select(User).where(User.id == first.user_id)
    )
    user = row.scalar_one()
    assert user.nickname.startswith("Telegram_")
    assert user.meta_data is not None
    assert user.meta_data["telegram_chat_id"] == telegram_chat_id
    assert user.meta_data["telegram_demo"] is True

    second = await provision_inty_for_telegram_chat(
        telegram_chat_id=telegram_chat_id,
        agent_id=agent_id,
    )
    assert second.is_new_user is False
    assert second.user_id == first.user_id

    await async_db_session.execute(delete(Chat).where(Chat.user_id == first.user_id))
    await _delete_user_and_agents(async_db_session, first.user_id)
    await async_db_session.execute(delete(Agent).where(Agent.id == agent_id))
    await async_db_session.execute(delete(User).where(User.id == creator_id))
    await async_db_session.commit()


@pytest.mark.asyncio
async def test_provision_onboard_creates_user_and_agent(
    async_db_session: AsyncSession,
) -> None:
    await async_engine.dispose()
    telegram_chat_id = f"tg-onboard-{uuid.uuid4().hex}"

    first = await provision_inty_for_telegram_onboard(
        telegram_chat_id=telegram_chat_id,
    )
    assert first.is_new_user is True
    assert first.agent_id != ""
    assert first.chat_id != ""

    second = await provision_inty_for_telegram_onboard(
        telegram_chat_id=telegram_chat_id,
    )
    assert second.is_new_user is False
    assert second.user_id == first.user_id
    assert second.agent_id == first.agent_id
    assert second.chat_id == first.chat_id

    await async_db_session.execute(delete(Chat).where(Chat.user_id == first.user_id))
    await _delete_user_and_agents(async_db_session, first.user_id)
    await async_db_session.commit()
