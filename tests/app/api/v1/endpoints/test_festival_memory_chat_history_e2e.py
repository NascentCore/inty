# CREATED_BY_AGENT
"""
节日记忆通过 Chat History API 投递的端到端测试。

流程：写入未投递的 festival memory -> 调用 GET /chats/agents/{agent_id}/messages
-> 断言响应中出现 festival_memory_prompt 且 festival_memory_id 匹配。
依赖本地后端 (localhost:8000) 与 config.yaml 的数据库配置。
"""

from datetime import date, datetime, timezone

import pytest
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.memory import Memory
from tests.app.api.test_client import TestClient

from loguru import logger

@pytest.fixture
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


def test_festival_memory_delivered_via_chat_history_api(
    integration_client: TestClient, db_session
):
    """
    端到端：写入一条未投递节日记忆 -> 调 GET messages -> 断言返回中含 festival_memory_prompt。
    """
    # 1) 创建 agent（同一用户已在 integration_client 中通过 guest 创建）
    agent_id = integration_client.create_agent()
    user_id = _decode_user_id_from_token(integration_client.token)

    # 2) 写入 memory 表：未投递的 festival 记忆
    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="festival",
        content="E2E test memory content",
        extracted_at=datetime.now(timezone.utc),
        festival_name="E2ETestFest",
        festival_date=date.today(),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)
    memory_id = memory.id

    try:
        # 3) 调用 Chat History API（触发按需投递并拉取消息）
        headers = dict(integration_client.client.headers)
        min_ver = (
            global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
        )
        if min_ver > 0:
            headers["appVersionCode"] = "9999"

        response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/chats/agents/{agent_id}/messages",
            params={"limit": 20, "offset": 0, "order": "desc"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()

        logger.info(f"data: {data}")

        # 4) 断言：至少有一条 festival_memory_prompt 且 festival_memory_id 匹配
        messages = data.get("messages", [])
        festival_prompts = [
            m
            for m in messages
            if m.get("type") == "festival_memory_prompt"
            and m.get("festival_memory_id") == memory_id
        ]
        assert (
            len(festival_prompts) >= 1
        ), f"Expected at least one message with type=festival_memory_prompt and festival_memory_id={memory_id}, got messages={messages}"
    finally:
        # 5) 清理：删除本测试插入的 Memory
        db_session.delete(memory)
        db_session.commit()
