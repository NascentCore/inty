"""Integration tests for chat endpoints using the custom TestClient."""

import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from jose import jwt
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.api.v1.endpoints import chat as chat_v1
from app.core.agent import agent as agent_module
from app.core.config import global_config_loaded_from_config_yaml
from app.models.memory import Memory
from app.models.user import AuthType
from app.schemas.response import BizError, BusinessErrorCode, UsageLimitExceeded
from app.services import agent_service, chat_history_service, chat_service
from app.services.global_services import subscription_service
from tests.app.api.test_client import TestClient
from tests.app.api.v1.endpoints.conftest import (
    _client_with_user,
    _create_mock_db_session,
    _make_user,
)


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


@pytest.fixture
def chat_business_error_app() -> FastAPI:
    app = FastAPI()
    app.include_router(chat_v1.router, prefix="/api/v1")

    async def override_db():
        mock_db = _create_mock_db_session()
        yield mock_db

    app.dependency_overrides[deps.get_async_db] = override_db

    yield app

    app.dependency_overrides.clear()


def _stub_chat_completion_dependencies(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_agent_for_chat(db, agent_id):
        return {"id": agent_id, "voice_id": "voice-1", "gender": "FEMALE"}

    class DummyAgent:
        async def chat(self, *args, **kwargs):  # pragma: no cover - not reached
            return "ok"

    async def fake_get_agent(agent_data):
        return DummyAgent()

    async def fake_check_chat_limit(db, user):
        return False, 5, 5

    def fake_add_user_message(session_id, message, meta_data=None):
        return None

    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(agent_service, "get_agent_for_chat", fake_get_agent_for_chat)
    monkeypatch.setattr(
        agent_module.agent_manager,
        "get_agent",
        fake_get_agent,
    )
    monkeypatch.setattr(
        subscription_service,
        "check_chat_limit",
        fake_check_chat_limit,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_user_message",
        fake_add_user_message,
    )


def _stub_generate_chat_image(monkeypatch: pytest.MonkeyPatch):
    async def fake_generate_chat_image(*args, **kwargs):
        return UsageLimitExceeded(
            code=BusinessErrorCode.SUBSCRIPTION_REQUIRED["code"],
            error_code=BusinessErrorCode.SUBSCRIPTION_REQUIRED["error_code"],
            message=BusinessErrorCode.SUBSCRIPTION_REQUIRED["message"],
            used_count=4,
            daily_limit=4,
        )

    monkeypatch.setattr(chat_service, "generate_chat_image", fake_generate_chat_image)


def _stub_generate_chat_image_blocked(monkeypatch: pytest.MonkeyPatch):
    async def fake_generate_chat_image(*args, **kwargs):
        return BizError(
            code=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["code"],
            error_code=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["error_code"],
            message=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["message"],
        )

    monkeypatch.setattr(chat_service, "generate_chat_image", fake_generate_chat_image)


def test_v1_chat_completions_guest_requires_login(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_chat_completion_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GUEST)

    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "zh",
    }

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.GUEST_LOGIN_REQUIRED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.GUEST_LOGIN_REQUIRED["error_code"]
    )
    assert body["data"]["used_count"] == 5
    assert body["data"]["daily_limit"] == 5


def test_v1_chat_completions_subscription_required(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_chat_completion_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "zh",
    }

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.SUBSCRIPTION_REQUIRED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.SUBSCRIPTION_REQUIRED["error_code"]
    )
    assert body["data"]["used_count"] == 5
    assert body["data"]["daily_limit"] == 5


def test_v1_chat_generate_image_wraps_business_error(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_generate_chat_image(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chat/images/agent-1",
            json={"message_id": 1},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.SUBSCRIPTION_REQUIRED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.SUBSCRIPTION_REQUIRED["error_code"]
    )
    assert body["data"]["used_count"] == 4
    assert body["data"]["daily_limit"] == 4


def test_v1_chat_generate_image_biz_error_matches_response_model(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_generate_chat_image_blocked(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chat/images/agent-1",
            json={"message_id": 1},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.IMAGE_GENERATION_BLOCKED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.IMAGE_GENERATION_BLOCKED["error_code"]
    )
    assert body["data"]["message"] == BusinessErrorCode.IMAGE_GENERATION_BLOCKED[
        "message"
    ]
    assert body["data"]["description"] == BusinessErrorCode.IMAGE_GENERATION_BLOCKED[
        "message"
    ]
    assert body["data"]["suggestion"] == "Please modify your prompt and try again."


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
    business_actions = data.get("business_actions")
    assert isinstance(business_actions, list) and len(business_actions) > 0
    for action in business_actions:
        assert isinstance(action, dict), f"Each business_actions item must be a dict: {action}"
        assert "action_type" in action and "message" in action, (
            f"Each business_actions item must have action_type and message: {action}"
        )


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
            "festival_date": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
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
            "festival_date": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
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
            "festival_date": date.today().isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
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
