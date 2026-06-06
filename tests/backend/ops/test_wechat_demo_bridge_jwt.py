"""Tests for WeChat demo bridge JWT remint on restore/persist."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.core.security import create_access_token
from app.db.session import async_engine
from app.models.agent import Agent, AgentStatus
from app.models.registry import load_model_modules
from app.models.user import AuthType, Gender, User
from backend.ops.wechat_demo.bridge_jwt import (
    BridgeJwtRemintError,
    BridgeJwtRemintInput,
    remint_bridge_inty_jwt,
)


@pytest.fixture
def sync_db_session():
    load_model_modules()
    from sqlalchemy import create_engine

    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def agent_fixture(sync_db_session):
    user_id = f"user-bridge-jwt-{uuid.uuid4().hex[:8]}"
    agent_id = f"agent-bridge-jwt-{uuid.uuid4().hex[:8]}"
    sync_db_session.add(
        User(
            id=user_id,
            auth_type=AuthType.GUEST,
            device_id=f"device-{uuid.uuid4().hex[:12]}",
        )
    )
    sync_db_session.flush()
    sync_db_session.add(
        Agent(
            id=agent_id,
            name="Bridge JWT Remint Test Agent",
            gender=Gender.FEMALE,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
        )
    )
    sync_db_session.commit()
    yield agent_id, user_id
    sync_db_session.execute(delete(Agent).where(Agent.id == agent_id))
    sync_db_session.execute(delete(User).where(User.id == user_id))
    sync_db_session.commit()


@pytest.mark.asyncio
async def test_remint_returns_valid_jwt(agent_fixture: tuple[str, str]) -> None:
    await async_engine.dispose()
    agent_id, user_id = agent_fixture
    stale = create_access_token(
        user_id,
        expires_delta=timedelta(seconds=-1),
    )
    fresh = await remint_bridge_inty_jwt(
        BridgeJwtRemintInput(agent_id=agent_id, inty_jwt=stale)
    )
    payload = jwt.decode(
        fresh,
        global_config_loaded_from_config_yaml.security.secret_key,
        algorithms=[global_config_loaded_from_config_yaml.security.algorithm],
    )
    assert payload["sub"] == user_id
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


@pytest.mark.asyncio
async def test_remint_missing_agent_raises() -> None:
    await async_engine.dispose()
    missing_agent_id = f"agent-missing-{uuid.uuid4().hex[:8]}"
    with pytest.raises(BridgeJwtRemintError):
        await remint_bridge_inty_jwt(
            BridgeJwtRemintInput(
                agent_id=missing_agent_id,
                inty_jwt="not-a-jwt",
            )
        )


@pytest.mark.asyncio
async def test_remint_rejects_jwt_sub_agent_mismatch(
    agent_fixture: tuple[str, str],
    sync_db_session,
) -> None:
    await async_engine.dispose()
    agent_id, _user_id = agent_fixture
    other_user_id = f"user-other-{uuid.uuid4().hex[:8]}"
    sync_db_session.add(
        User(
            id=other_user_id,
            auth_type=AuthType.GUEST,
            device_id=f"device-{uuid.uuid4().hex[:12]}",
        )
    )
    sync_db_session.commit()
    mismatched = create_access_token(other_user_id)
    try:
        with pytest.raises(BridgeJwtRemintError):
            await remint_bridge_inty_jwt(
                BridgeJwtRemintInput(agent_id=agent_id, inty_jwt=mismatched)
            )
    finally:
        sync_db_session.execute(delete(User).where(User.id == other_user_id))
        sync_db_session.commit()
