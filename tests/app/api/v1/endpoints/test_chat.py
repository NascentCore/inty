"""Integration tests for chat endpoints using the custom TestClient."""

import json
from datetime import date, datetime, timezone

import pytest
from jose import jwt
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.memory import Memory
from tests.app.api.test_client import TestClient


@pytest.fixture(scope="function")
def db_session():
    """提供数据库会话，与后端共用 config.yaml 的 database.url。"""
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _decode_user_id_from_token(token: str) -> str:
    """从 JWT 解析 user_id（sub），与 create_access_token 一致。"""
    payload = jwt.decode(
        token,
        global_config_loaded_from_config_yaml.security.secret_key,
        algorithms=[global_config_loaded_from_config_yaml.security.algorithm],
    )
    return str(payload["sub"])


@pytest.fixture(scope="function")
def agent_ids_to_cleanup(integration_client: TestClient):
    agent_ids = []
    yield agent_ids
    for agent_id in agent_ids:
        logger.info(f"Deleting agent: {agent_id}")
        integration_client.delete_agent(agent_id)
        logger.info(f"Deleted agent: {agent_id}")


@pytest.mark.noci
def test_agent_chat_completions_with_sdk(
    integration_client: TestClient, agent_ids_to_cleanup
):
    """Test chat completions using the custom TestClient."""
    agent_id = integration_client.create_agent(
        name="Test Agent",
        gender="MALE",
        visibility="PUBLIC",
    )
    agent_ids_to_cleanup.append(agent_id)

    messages = [{"role": "user", "content": "Hello, how are you?"}]

    response = integration_client.chat_completions(
        agent_id,
        messages,
        language="en",
    )

    logger.info(
        "Chat completion full HTTP response:\n{}",
        json.dumps(response, indent=2, ensure_ascii=False),
    )

    assert response is not None
    assert response.get("code") == 200
    assert response.get("data") is not None

    data = response["data"]
    choices = data.get("choices")
    assert isinstance(choices, list) and len(choices) > 0
    message = choices[0].get("message")
    assert message is not None
    assert "id" in message
    assert isinstance(message["id"], int)


def test_festival_memory_delivered_via_chat_completions(
    integration_client: TestClient, agent_ids_to_cleanup, db_session
):
    """
    端到端：写入一条未投递节日记忆 -> 调 POST chat completions（带满足最低版本的 appVersionCode）-> 断言响应 choices 中含 festival_memory_prompt。
    """
    min_ver = (
        global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
    )
    if min_ver == 0:
        pytest.skip(
            "min_app_version_code_for_festival_memory is 0, version gating not in effect"
        )

    agent_id = integration_client.create_agent(
        name="Test Agent Festival",
        gender="MALE",
        visibility="PUBLIC",
    )
    agent_ids_to_cleanup.append(agent_id)
    user_id = _decode_user_id_from_token(integration_client.token)

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="festival",
        content="E2E test memory for chat completions",
        meta_data={
            "festival_name": "E2ETestFestCompletions",
            "festival_data": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
        festival_name="E2ETestFestCompletions",
        festival_date=date.today(),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)
    memory_id = memory.id

    try:
        response = integration_client.chat_completions(
            agent_id,
            [{"role": "user", "content": "Hi"}],
            language="en",
            headers={"appVersionCode": str(min_ver)},
        )
        logger.info(f"response: {response}")
        assert response.get("code") == 200, response
        data = response.get("data", {})
        choices = data.get("choices", [])
        festival_prompts = [
            c
            for c in choices
            if c.get("message", {}).get("type") == "festival_memory_prompt"
            and c.get("message", {}).get("festival_memory_id") == memory_id
        ]
        assert (
            len(festival_prompts) >= 1
        ), f"Expected at least one choice with type=festival_memory_prompt and festival_memory_id={memory_id}, got choices={choices}"
        msg = festival_prompts[0].get("message", {})
        assert "id" in msg, f"Festival memory prompt message must have id, got message={msg}"
        assert isinstance(msg["id"], int), f"Festival memory prompt message id must be int, got {type(msg['id']).__name__}"
        # 断言：投递后 memory.delivery_at 已更新
        db_session.refresh(memory)
        assert memory.delivery_at is not None, "memory.delivery_at should be set after delivery"
    finally:
        db_session.delete(memory)
        db_session.commit()


def test_festival_memory_chat_completions_gated_by_app_version(
    integration_client: TestClient, agent_ids_to_cleanup, db_session
):
    """
    当 appVersionCode 低于 min_app_version_code_for_festival_memory 时，
    POST chat completions 响应中不包含 festival_memory_prompt 类型的 choice。
    """
    min_ver = (
        global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
    )
    if min_ver == 0:
        pytest.skip(
            "min_app_version_code_for_festival_memory is 0, version gating not in effect"
        )

    agent_id = integration_client.create_agent(
        name="Test Agent Festival Gated",
        gender="MALE",
        visibility="PUBLIC",
    )
    agent_ids_to_cleanup.append(agent_id)
    user_id = _decode_user_id_from_token(integration_client.token)

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="festival",
        content="E2E test memory for version gating",
        meta_data={
            "festival_name": "E2ETestFestGated",
            "festival_data": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
        festival_name="E2ETestFestGated",
        festival_date=date.today(),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)

    try:
        response = integration_client.chat_completions(
            agent_id,
            [{"role": "user", "content": "Hi"}],
            language="en",
            headers={"appVersionCode": str(min_ver - 1)},
        )
        assert response.get("code") == 200, response
        data = response.get("data", {})
        choices = data.get("choices", [])
        festival_prompts = [
            c
            for c in choices
            if c.get("message", {}).get("type") == "festival_memory_prompt"
        ]
        assert (
            len(festival_prompts) == 0
        ), f"Expected no festival_memory_prompt when appVersionCode < min_ver, got {festival_prompts}"
        # 旧版不投递，delivery_at 保持 null（与 FR 一致）
        db_session.refresh(memory)
        assert memory.delivery_at is None, (
            "When app version is too old, delivery must be skipped and delivery_at must remain null"
        )
    finally:
        db_session.delete(memory)
        db_session.commit()


def test_festival_memory_old_app_version_completions_delivery_at_stays_null(
    integration_client: TestClient, agent_ids_to_cleanup, db_session
):
    """
    当 appVersionCode 低于 min_app_version_code_for_festival_memory 时，
    POST chat completions 不触发投递，memory.delivery_at 保持 null。
    """
    min_ver = (
        global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
    )
    if min_ver == 0:
        pytest.skip(
            "min_app_version_code_for_festival_memory is 0, version gating not in effect"
        )

    agent_id = integration_client.create_agent(
        name="Test Festival Old App Null",
        gender="MALE",
        visibility="PUBLIC",
    )
    agent_ids_to_cleanup.append(agent_id)
    user_id = _decode_user_id_from_token(integration_client.token)

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="festival",
        content="E2E test memory for old app completions delivery_at null",
        meta_data={
            "festival_name": "E2ETestFestCompletionsNull",
            "festival_data": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
        festival_name="E2ETestFestCompletionsNull",
        festival_date=date.today(),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)

    try:
        response = integration_client.chat_completions(
            agent_id,
            [{"role": "user", "content": "Hi"}],
            language="en",
            headers={"appVersionCode": str(min_ver - 1)},
        )
        assert response.get("code") == 200, response
        data = response.get("data", {})
        choices = data.get("choices", [])
        festival_prompts = [
            c
            for c in choices
            if c.get("message", {}).get("type") == "festival_memory_prompt"
        ]
        assert (
            len(festival_prompts) == 0
        ), f"Expected no festival_memory_prompt when appVersionCode < min_ver, got {festival_prompts}"
        db_session.refresh(memory)
        assert memory.delivery_at is None, (
            "When app version is too old, delivery must be skipped and delivery_at must remain null"
        )
    finally:
        db_session.delete(memory)
        db_session.commit()
