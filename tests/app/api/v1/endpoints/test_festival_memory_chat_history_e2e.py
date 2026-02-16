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
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.memory import Memory
from tests.app.api.test_client import TestClient

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


def _festival_prompts_for_memory(messages: list, memory_id: int) -> list:
    """Return messages that are festival_memory_prompt for the given memory_id."""
    return [
        m
        for m in messages
        if m.get("type") == "festival_memory_prompt"
        and m.get("festival_memory_id") == memory_id
    ]


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
        meta_data={
            "festival_name": "E2ETestFest",
            "festival_data": date.today().isoformat(),
        },
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
        data = integration_client.get_agent_chat_messages(agent_id)
        logger.info(f"data: {data}")

        # 4) 断言：至少有一条 festival_memory_prompt 且 festival_memory_id 匹配
        messages = data.get("messages", [])
        festival_prompts = _festival_prompts_for_memory(messages, memory_id)
        assert (
            len(festival_prompts) >= 1
        ), f"Expected at least one message with type=festival_memory_prompt and festival_memory_id={memory_id}, got messages={messages}"
        # 5) 断言：投递后 memory.delivery_at 已更新
        db_session.refresh(memory)
        assert memory.delivery_at is not None, "memory.delivery_at should be set after delivery"
        assert getattr(memory.delivery_at, "tzinfo", None) is not None, "memory.delivery_at should be timezone-aware"
    finally:
        # 6) 清理：删除本测试插入的 Memory
        db_session.delete(memory)
        db_session.commit()


def test_festival_memory_delivery_at_set_and_second_get_idempotent(
    integration_client: TestClient, db_session
):
    """
    端到端：第一次 GET 投递节日记忆并设置 delivery_at；第二次 GET 不再重复投递，列表中仍仅有一条该记忆的提示。
    """
    agent_id = integration_client.create_agent()
    user_id = _decode_user_id_from_token(integration_client.token)

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="festival",
        content="E2E idempotent test memory",
        meta_data={
            "festival_name": "E2ETestFestIdem",
            "festival_data": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
        festival_name="E2ETestFestIdem",
        festival_date=date.today(),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)
    memory_id = memory.id

    try:
        # 1) First GET -> delivery happens
        data1 = integration_client.get_agent_chat_messages(agent_id)
        messages1 = data1.get("messages", [])
        festival1 = _festival_prompts_for_memory(messages1, memory_id)
        assert len(festival1) >= 1, (
            f"Expected at least one festival_memory_prompt for memory_id={memory_id}, got messages={messages1}"
        )
        # 2) Assert DB: delivery_at set
        db_session.refresh(memory)
        assert memory.delivery_at is not None, "memory.delivery_at should be set after first GET"
        # 3) Second GET
        data2 = integration_client.get_agent_chat_messages(agent_id)
        messages2 = data2.get("messages", [])
        # 4) Idempotency: still exactly one prompt for this memory (no duplicate)
        festival2 = _festival_prompts_for_memory(messages2, memory_id)
        assert len(festival2) == 1, (
            f"Expected exactly one festival_memory_prompt for memory_id={memory_id} after second GET (idempotent), got count={len(festival2)}, messages={messages2}"
        )
    finally:
        db_session.delete(memory)
        db_session.commit()


def test_festival_memory_messages_gated_by_app_version(
    integration_client: TestClient, db_session
):
    """
    当 appVersionCode 低于 min_app_version_code_for_festival_memory 时，
    GET messages 响应中不包含 festival_memory_prompt 类型的消息。
    """
    min_ver = (
        global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
    )
    if min_ver == 0:
        pytest.skip(
            "min_app_version_code_for_festival_memory is 0, version gating not in effect"
        )

    agent_id = integration_client.create_agent()
    user_id = _decode_user_id_from_token(integration_client.token)

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="festival",
        content="E2E test memory for messages gate",
        meta_data={
            "festival_name": "E2ETestFestMessagesGate",
            "festival_data": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
        festival_name="E2ETestFestMessagesGate",
        festival_date=date.today(),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)

    try:
        # 先触发投递并确认列表中有该提示
        integration_client.get_agent_chat_messages(agent_id)
        db_session.refresh(memory)
        assert memory.delivery_at is not None

        # 低版本 header 拉取：应不返回 festival_memory_prompt
        data = integration_client.get_agent_chat_messages(
            agent_id,
            headers={"appVersionCode": str(min_ver - 1)},
        )
        messages = data.get("messages", [])
        festival_in_messages = [
            m for m in messages if m.get("type") == "festival_memory_prompt"
        ]
        assert (
            len(festival_in_messages) == 0
        ), f"Expected no festival_memory_prompt when appVersionCode < min_ver, got {festival_in_messages}"
    finally:
        db_session.delete(memory)
        db_session.commit()


def test_festival_memory_agent_detail_gated_by_app_version(
    integration_client: TestClient, db_session
):
    """
    当 appVersionCode 满足/低于 min_app_version_code_for_festival_memory 时，
    GET agent 响应中 features.festival_memories 应有/无。
    """
    min_ver = (
        global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
    )
    if min_ver == 0:
        pytest.skip(
            "min_app_version_code_for_festival_memory is 0, version gating not in effect"
        )

    agent_id = integration_client.create_agent()
    user_id = _decode_user_id_from_token(integration_client.token)

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="festival",
        content="E2E test memory for agent detail gate",
        meta_data={
            "festival_name": "E2ETestFestAgentGate",
            "festival_data": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
        festival_name="E2ETestFestAgentGate",
        festival_date=date.today(),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()

    try:
        # 高版本：应返回 festival_memories
        resp_high = integration_client.get_agent(
            agent_id,
            headers=integration_client.headers_for_festival_memory(),
        )
        assert resp_high.get("code") == 200, resp_high
        data_high = resp_high.get("data", {})
        features_high = data_high.get("features") or {}
        festival_list_high = features_high.get("festival_memories") or []
        assert (
            len(festival_list_high) >= 1
        ), f"Expected festival_memories when appVersionCode >= min_ver, got features={features_high}"

        # 低版本：不返回 festival_memories（或为空）
        resp_low = integration_client.get_agent(
            agent_id,
            headers={"appVersionCode": str(min_ver - 1)},
        )
        assert resp_low.get("code") == 200, resp_low
        data_low = resp_low.get("data", {})
        features_low = data_low.get("features") or {}
        festival_list_low = features_low.get("festival_memories") or []
        assert (
            len(festival_list_low) == 0
        ), f"Expected no festival_memories when appVersionCode < min_ver, got festival_memories={festival_list_low}"
    finally:
        db_session.delete(memory)
        db_session.commit()
