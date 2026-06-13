"""Tests for Weixin onboard Inty user + agent provisioning."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal, async_engine
from app.models.agent import Agent
from app.models.registry import load_model_modules
from app.models.user import User
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    add_guest_user,
)
from backend.ops.weixin_onboard.provision import provision_inty_for_ilink_user
from tests.app.services.agentic_channel.companion_test_fixtures import (
    assert_companion_guest_identity_has_no_readable_id,
)


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
async def test_provision_create_and_reuse(async_db_session: AsyncSession) -> None:
    """Single async test: global ``AsyncSessionLocal`` breaks a second async DB test."""
    await async_engine.dispose()
    ilink_user_id = f"ilink-{uuid.uuid4().hex}"

    first = await provision_inty_for_ilink_user(ilink_user_id=ilink_user_id)
    assert first.is_new_user is True
    assert first.user_id != ""
    assert first.agent_id != ""
    assert first.jwt != ""

    row = await async_db_session.execute(
        select(User).where(User.id == first.user_id)
    )
    user = row.scalar_one()
    assert user.meta_data is not None
    assert user.meta_data["ilink_user_id"] == ilink_user_id

    agent_row = await async_db_session.execute(
        select(Agent).where(Agent.id == first.agent_id)
    )
    agent = agent_row.scalar_one()
    assert agent.creator_id == first.user_id
    assert_companion_guest_identity_has_no_readable_id(user=user, agent=agent)

    second = await provision_inty_for_ilink_user(ilink_user_id=ilink_user_id)
    assert second.is_new_user is False
    assert second.user_id == first.user_id
    assert second.agent_id == first.agent_id
    assert second.jwt != ""

    await _delete_user_and_agents(async_db_session, first.user_id)


@pytest.mark.asyncio
async def test_provision_adds_agent_for_existing_user_without_agent(
    async_db_session: AsyncSession,
) -> None:
    await async_engine.dispose()
    ilink_user_id = f"ilink-{uuid.uuid4().hex}"
    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix="Weixin",
                meta_data={"ilink_user_id": ilink_user_id},
            ),
        )
        await db.commit()
        orphan_user_id = user.id

    result = await provision_inty_for_ilink_user(ilink_user_id=ilink_user_id)
    assert result.is_new_user is False
    assert result.user_id == orphan_user_id
    assert result.agent_id != ""
    assert result.jwt != ""

    agent_row = await async_db_session.execute(
        select(Agent).where(Agent.id == result.agent_id)
    )
    agent = agent_row.scalar_one()
    user_row = await async_db_session.execute(
        select(User).where(User.id == orphan_user_id)
    )
    user = user_row.scalar_one()
    assert agent.creator_id == orphan_user_id
    assert agent.name.startswith("weixin-companion-")
    assert_companion_guest_identity_has_no_readable_id(user=user, agent=agent)

    await _delete_user_and_agents(async_db_session, orphan_user_id)
