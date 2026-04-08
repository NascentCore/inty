"""Integration tests for chat endpoints using the custom TestClient."""

import asyncio
import json
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient as FastAPITestClient
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
from app.schemas.response import APIResponse, BizError, BusinessErrorCode, UsageLimitExceeded
from app.services.voice_service import (
    VoiceGenerationResult,
    voice_service as global_voice_service,
)
from app.services import agent_service, chat_history_service, chat_service
from app.services.global_services import subscription_service as global_subscription_service
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
        global_subscription_service,
        "check_chat_limit",
        fake_check_chat_limit,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_user_message",
        fake_add_user_message,
    )


def _stub_chat_completion_dependencies_capture_user_save(
    monkeypatch: pytest.MonkeyPatch,
) -> list:
    """Same as _stub_chat_completion_dependencies but records add_user_message calls."""
    calls: list = []

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
        calls.append(
            {"session_id": session_id, "message": message, "meta_data": meta_data}
        )
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
        global_subscription_service,
        "check_chat_limit",
        fake_check_chat_limit,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_user_message",
        fake_add_user_message,
    )
    return calls


def _stub_success_chat_completion_with_premium_preview(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_agent_for_chat(db, agent_id):
        return {"id": agent_id, "voice_id": "voice-1", "gender": "FEMALE"}

    class DummyAgent:
        async def chat(self, *args, **kwargs):
            return ("free-mode response", 101)

        async def generate_message_without_user_save(self, *args, **kwargs):
            return (
                "A warmer and more personalized premium-only response sample.",
                None,
            )

    async def fake_get_agent(agent_data):
        return DummyAgent()

    async def fake_check_chat_limit(db, user):
        # used_count=4 -> 第 5 条触发预览（默认 every_n=5）
        return True, 4, 100

    async def fake_get_user_current_subscription(db, user_id):
        return None

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            voice_enabled=False,
            style_prompt=None,
            premium_mode=False,
            language="en",
        )

    async def fake_record_usage(*args, **kwargs):
        return None

    async def fake_get_ai_message_info_by_id(db, message_id):
        return {
            "id": message_id,
            "meta_data": {"source": "unit-test"},
            "timestamp": 1735689600000,
            "audio_url": None,
        }

    async def fake_get_latest_user_message_id(db, session_id):
        return 55

    async def fake_mark_user_push_notifications_as_read(db, user_id):
        return 0

    async def fake_try_trigger_surprise_snap(db, session_id, user_id, agent_id):
        return None

    monkeypatch.setattr(
        global_config_loaded_from_config_yaml.agent,
        "enable_free_user_premium_preview",
        True,
    )
    monkeypatch.setattr(
        global_config_loaded_from_config_yaml.agent,
        "free_user_premium_preview_every_n_messages",
        5,
    )
    monkeypatch.setattr(
        global_config_loaded_from_config_yaml.agent,
        "free_user_premium_preview_max_chars",
        280,
    )

    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(agent_service, "get_agent_for_chat", fake_get_agent_for_chat)
    monkeypatch.setattr(
        agent_module.agent_manager,
        "get_agent",
        fake_get_agent,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "check_chat_limit",
        fake_check_chat_limit,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "record_usage",
        fake_record_usage,
    )
    monkeypatch.setattr(
        chat_history_service,
        "get_ai_message_info_by_id",
        fake_get_ai_message_info_by_id,
    )
    monkeypatch.setattr(
        chat_history_service,
        "get_latest_user_message_id",
        fake_get_latest_user_message_id,
    )
    monkeypatch.setattr(
        chat_v1,
        "mark_user_push_notifications_as_read",
        fake_mark_user_push_notifications_as_read,
    )
    monkeypatch.setattr(
        chat_v1,
        "try_trigger_surprise_snap",
        fake_try_trigger_surprise_snap,
    )


def _stub_success_chat_completion_with_multimodal(
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    captured: dict = {}

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_agent_for_chat(db, agent_id):
        return {"id": agent_id, "voice_id": "voice-1", "gender": "FEMALE"}

    class DummyAgent:
        async def chat(self, *args, **kwargs):
            captured["messages"] = kwargs.get("messages")
            captured["client_local_message_id"] = kwargs.get(
                "client_local_message_id"
            )
            return ("multimodal response", 301)

    async def fake_get_agent(agent_data):
        return DummyAgent()

    async def fake_check_chat_limit(db, user):
        return True, 0, 100

    async def fake_get_user_current_subscription(db, user_id):
        return None

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            voice_enabled=False,
            style_prompt=None,
            premium_mode=False,
            language="en",
        )

    async def fake_record_usage(*args, **kwargs):
        return None

    async def fake_get_ai_message_info_by_id(db, message_id):
        return {
            "id": message_id,
            "meta_data": {"source": "multimodal-test"},
            "timestamp": "2026-03-02T00:00:00Z",
            "audio_url": None,
        }

    async def fake_get_latest_user_message_id(db, session_id):
        return 77

    async def fake_mark_user_push_notifications_as_read(db, user_id):
        return 0

    async def fake_try_trigger_surprise_snap(db, session_id, user_id, agent_id):
        return None

    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(agent_service, "get_agent_for_chat", fake_get_agent_for_chat)
    monkeypatch.setattr(
        agent_module.agent_manager,
        "get_agent",
        fake_get_agent,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "check_chat_limit",
        fake_check_chat_limit,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "record_usage",
        fake_record_usage,
    )
    monkeypatch.setattr(
        chat_history_service,
        "get_ai_message_info_by_id",
        fake_get_ai_message_info_by_id,
    )
    monkeypatch.setattr(
        chat_history_service,
        "get_latest_user_message_id",
        fake_get_latest_user_message_id,
    )
    monkeypatch.setattr(
        chat_v1,
        "mark_user_push_notifications_as_read",
        fake_mark_user_push_notifications_as_read,
    )
    monkeypatch.setattr(
        chat_v1,
        "try_trigger_surprise_snap",
        fake_try_trigger_surprise_snap,
    )
    return captured


def _stub_success_chat_completion_with_multimodal_response(
    monkeypatch: pytest.MonkeyPatch,
    response_content,
):
    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_agent_for_chat(db, agent_id):
        return {"id": agent_id, "voice_id": "voice-1", "gender": "FEMALE"}

    class DummyAgent:
        async def chat(self, *args, **kwargs):
            return (response_content, 401)

    async def fake_get_agent(agent_data):
        return DummyAgent()

    async def fake_check_chat_limit(db, user):
        return True, 0, 100

    async def fake_get_user_current_subscription(db, user_id):
        return None

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            voice_enabled=False,
            style_prompt=None,
            premium_mode=False,
            language="en",
        )

    async def fake_record_usage(*args, **kwargs):
        return None

    async def fake_get_ai_message_info_by_id(db, message_id):
        return {
            "id": message_id,
            "meta_data": {"source": "multimodal-response-test"},
            "timestamp": "2026-03-02T00:00:00Z",
            "audio_url": None,
        }

    async def fake_get_latest_user_message_id(db, session_id):
        return 88

    async def fake_mark_user_push_notifications_as_read(db, user_id):
        return 0

    async def fake_try_trigger_surprise_snap(db, session_id, user_id, agent_id):
        return None

    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(agent_service, "get_agent_for_chat", fake_get_agent_for_chat)
    monkeypatch.setattr(
        agent_module.agent_manager,
        "get_agent",
        fake_get_agent,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "check_chat_limit",
        fake_check_chat_limit,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "record_usage",
        fake_record_usage,
    )
    monkeypatch.setattr(
        chat_history_service,
        "get_ai_message_info_by_id",
        fake_get_ai_message_info_by_id,
    )
    monkeypatch.setattr(
        chat_history_service,
        "get_latest_user_message_id",
        fake_get_latest_user_message_id,
    )
    monkeypatch.setattr(
        chat_v1,
        "mark_user_push_notifications_as_read",
        fake_mark_user_push_notifications_as_read,
    )
    monkeypatch.setattr(
        chat_v1,
        "try_trigger_surprise_snap",
        fake_try_trigger_surprise_snap,
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


def _stub_generate_chat_music(monkeypatch: pytest.MonkeyPatch):
    async def fake_generate_chat_music(*args, **kwargs):
        return UsageLimitExceeded(
            code=BusinessErrorCode.SUBSCRIPTION_REQUIRED["code"],
            error_code=BusinessErrorCode.SUBSCRIPTION_REQUIRED["error_code"],
            message=BusinessErrorCode.SUBSCRIPTION_REQUIRED["message"],
            used_count=2,
            daily_limit=2,
        )

    monkeypatch.setattr(chat_service, "generate_chat_music", fake_generate_chat_music)


def _stub_generate_chat_music_success(monkeypatch: pytest.MonkeyPatch):
    async def fake_generate_chat_music(*args, **kwargs):
        return chat_v1.schemas.ChatMusicGenerationResponse(
            audio_url="https://cdn.example.com/music.mp3",
            audio_metadata={"format": "mp3", "duration_sec": 12.3, "provider": "fal"},
            prompt="music prompt",
            message_id=1,
            model="fal-ai/stable-audio",
            generation_time_ms=520,
        )

    monkeypatch.setattr(chat_service, "generate_chat_music", fake_generate_chat_music)


def test_v1_chat_completions_guest_saves_local_id_meta_on_limit(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    calls = _stub_chat_completion_dependencies_capture_user_save(monkeypatch)
    user = _make_user(auth_type=AuthType.GUEST)
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "zh",
        "localId": "guest-limit-local-1",
    }
    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)
    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["meta_data"] == {"localId": "guest-limit-local-1"}


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


def test_v1_chat_completions_adds_premium_preview_and_popup_action(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_success_chat_completion_with_premium_preview(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
    }

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 200

    data = body["data"]
    actions = data["business_actions"]
    assert isinstance(actions, list) and len(actions) > 0
    assert actions[0]["action_type"] == "subscription_popup"
    assert actions[0]["message"]

    choices = data["choices"]
    premium_preview_choices = [
        c
        for c in choices
        if c.get("message", {}).get("type") == "premium_preview"
    ]
    assert len(premium_preview_choices) == 1
    premium_content = premium_preview_choices[0]["message"]["content"]
    assert "Premium-only preview:" in premium_content
    assert "Subscribe to Premium" in premium_content


def test_v1_chat_completions_accepts_multimodal_user_content(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured = _stub_success_chat_completion_with_multimodal(monkeypatch)
    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please describe this picture."},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://cdn.example.com/test.jpg"},
                    },
                ],
            }
        ],
        "stream": False,
        "model": "chatbot",
        "language": "en",
    }

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 200
    assert body["data"]["choices"][0]["message"]["content"] == "multimodal response"
    assert body["data"]["usage"]["prompt_tokens"] == 4

    sent_messages = captured.get("messages")
    assert sent_messages is not None and len(sent_messages) == 1
    sent_content = sent_messages[0].content
    assert isinstance(sent_content, list)
    assert sent_content[0]["type"] == "text"
    assert sent_content[0]["text"] == "Please describe this picture."
    assert sent_content[1]["type"] == "image_url"
    assert sent_content[1]["image_url"]["url"] == "https://cdn.example.com/test.jpg"


def test_v1_chat_completions_forwards_local_id_to_agent(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured = _stub_success_chat_completion_with_multimodal(monkeypatch)
    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
        "localId": "temp-client-1",
    }
    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)
    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert captured.get("client_local_message_id") == "temp-client-1"


def test_v1_chat_completions_message_id_fallback_when_local_id_absent(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured = _stub_success_chat_completion_with_multimodal(monkeypatch)
    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
        "message_id": "legacy-msg-id-9",
    }
    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)
    assert response.status_code == 200
    assert captured.get("client_local_message_id") == "legacy-msg-id-9"


def test_v1_chat_completions_local_id_preferred_over_message_id(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured = _stub_success_chat_completion_with_multimodal(monkeypatch)
    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
        "localId": "preferred",
        "message_id": "ignored",
    }
    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)
    assert response.status_code == 200
    assert captured.get("client_local_message_id") == "preferred"


def test_v1_chat_completions_returns_source_imate_id_when_target_imate_id_sent(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_success_chat_completion_with_multimodal_response(
        monkeypatch,
        response_content="source image id response",
    )
    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [{"role": "user", "content": "show me"}],
        "target_imate_id": "imate-target-1",
    }
    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 200
    assert body["data"]["source_imate_id"] == "imate-target-1"


def test_chat_websocket_reuses_connection_for_multiple_agents(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    user = _make_user(auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    async def fake_agent_chat_completions(
        *,
        db,
        agent_id,
        request,
        current_user,
        app_version_code,
        subscription_svc,
        voice_svc,
    ):
        return APIResponse.success(
            data={
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": f"reply:{agent_id}"},
                        "finish_reason": "stop",
                    }
                ],
                "source_imate_id": request.target_imate_id,
            }
        )

    monkeypatch.setattr(chat_v1, "_get_current_user_from_websocket", fake_ws_user)
    monkeypatch.setattr(chat_v1, "agent_chat_completions", fake_agent_chat_completions)

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-a",
                    "request": {
                        "messages": [{"role": "user", "content": "hello a"}],
                        "target_imate_id": "imate-a",
                    },
                }
            )
            first_response = websocket.receive_json()

            websocket.send_json(
                {
                    "agent_id": "agent-b",
                    "request": {
                        "messages": [{"role": "user", "content": "hello b"}],
                        "target_imate_id": "imate-b",
                    },
                }
            )
            second_response = websocket.receive_json()

    assert first_response["code"] == 200
    assert first_response["agent_id"] == "agent-a"
    assert first_response["data"]["source_imate_id"] == "imate-a"

    assert second_response["code"] == 200
    assert second_response["agent_id"] == "agent-b"
    assert second_response["data"]["source_imate_id"] == "imate-b"


def test_chat_websocket_idle_timeout_reads_config(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    """Regression: idle wait uses app.features.chat_ws_idle_timeout_seconds (not a hard-coded constant)."""
    user = _make_user(auth_type=AuthType.GOOGLE)
    captured = {"timeouts": []}

    async def fake_ws_user(websocket, db):
        return user

    async def fake_agent_chat_completions(**kwargs):
        return APIResponse.success(data={"choices": []})

    async def fake_wait_for(aw, timeout):
        captured["timeouts"].append(timeout)
        if len(captured["timeouts"]) == 1:
            return await aw
        raise asyncio.TimeoutError()

    monkeypatch.setattr(chat_v1, "_get_current_user_from_websocket", fake_ws_user)
    monkeypatch.setattr(chat_v1, "agent_chat_completions", fake_agent_chat_completions)
    monkeypatch.setattr(chat_v1.asyncio, "wait_for", fake_wait_for)

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-a",
                    "request": {"messages": [{"role": "user", "content": "hi"}]},
                }
            )
            websocket.receive_json()

    expected = float(
        global_config_loaded_from_config_yaml.app.features.chat_ws_idle_timeout_seconds
    )
    assert captured["timeouts"] and all(t == expected for t in captured["timeouts"])


def test_chat_websocket_assume_user_id_ignored_for_non_superuser(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    user = _make_user(user_id="user-1", auth_type=AuthType.GOOGLE, is_superuser=False)
    captured: dict = {}

    async def fake_ws_user(websocket, db):
        return user

    async def fake_agent_chat_completions(
        *,
        db,
        agent_id,
        request,
        current_user,
        app_version_code,
        subscription_svc,
        voice_svc,
    ):
        captured["effective_user_id"] = current_user.id
        return APIResponse.success(
            data={
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
            }
        )

    monkeypatch.setattr(chat_v1, "_get_current_user_from_websocket", fake_ws_user)
    monkeypatch.setattr(chat_v1, "agent_chat_completions", fake_agent_chat_completions)

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect(
            "/api/v1/chat/ws?assume_user_id=user-other"
        ) as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-a",
                    "request": {"messages": [{"role": "user", "content": "hi"}]},
                }
            )
            websocket.receive_json()

    assert captured.get("effective_user_id") == "user-1"


def test_chat_websocket_client_context_fills_time_context_when_request_omits_it(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    user = _make_user(auth_type=AuthType.GOOGLE)
    captured: dict = {}

    async def fake_ws_user(websocket, db):
        return user

    async def fake_agent_chat_completions(
        *,
        db,
        agent_id,
        request,
        current_user,
        app_version_code,
        subscription_svc,
        voice_svc,
    ):
        captured["user_time_context"] = request.user_time_context
        return APIResponse.success(
            data={
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
            }
        )

    monkeypatch.setattr(chat_v1, "_get_current_user_from_websocket", fake_ws_user)
    monkeypatch.setattr(chat_v1, "agent_chat_completions", fake_agent_chat_completions)

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "client_context",
                    "time_context": {
                        "local_time": "2026-04-07T08:00:00+08:00",
                        "timezone": "Asia/Shanghai",
                        "utc_offset_minutes": 480,
                    },
                }
            )
            assert websocket.receive_json() == {"type": "client_context_ack", "ok": True}
            websocket.send_json(
                {
                    "agent_id": "agent-a",
                    "request": {
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                }
            )
            chat_response = websocket.receive_json()

    assert chat_response["code"] == 200
    utc = captured.get("user_time_context")
    assert utc is not None
    assert utc.timezone == "Asia/Shanghai"
    assert utc.utc_offset_minutes == 480


def test_v1_chat_completions_prefers_chat_settings_voice_id_for_autoplay(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured_voice_id = {}

    _stub_success_chat_completion_with_multimodal_response(
        monkeypatch,
        response_content="voice me",
    )

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            voice_enabled=True,
            voice_id="google/Zephyr",
            style_prompt=None,
            premium_mode=False,
            language="en",
        )

    async def fake_generate_voice(*args, **kwargs):
        captured_voice_id["value"] = kwargs.get("voice_id")
        return VoiceGenerationResult(
            gcs_url="gs://test-bucket/voice/202603/voice_test.wav",
            gcs_http_url="https://storage.googleapis.com/test-bucket/voice/202603/voice_test.wav",
            duration_seconds=1.23,
        )

    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(global_voice_service, "generate_voice", fake_generate_voice)

    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
    }

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 200
    assert captured_voice_id["value"] == "google/Zephyr"


def test_v1_chat_completions_returns_text_and_image_content_parts(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_success_chat_completion_with_multimodal_response(
        monkeypatch,
        response_content=[
            {"type": "text", "text": "Here is the image you asked for."},
            {
                "type": "image_url",
                "image_url": {"url": "https://cdn.example.com/ai-result.webp"},
            },
        ],
    )
    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [{"role": "user", "content": "show me a sunset"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
    }

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 200
    message = body["data"]["choices"][0]["message"]
    assert message["content"] == "Here is the image you asked for."
    assert message["content_parts"][0]["type"] == "text"
    assert message["content_parts"][1]["type"] == "image_url"
    assert (
        message["content_parts"][1]["image_url"]["url"]
        == "https://cdn.example.com/ai-result.webp"
    )


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


def test_v1_chat_generate_music_wraps_business_error(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_generate_chat_music(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chat/music/agent-1",
            json={"message_id": 1},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.SUBSCRIPTION_REQUIRED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.SUBSCRIPTION_REQUIRED["error_code"]
    )
    assert body["data"]["used_count"] == 2
    assert body["data"]["daily_limit"] == 2


def test_v1_chat_generate_music_success(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_generate_chat_music_success(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chat/music/agent-1",
            json={"message_id": 1},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 200
    assert body["data"]["audio_url"] == "https://cdn.example.com/music.mp3"
    assert body["data"]["model"] == "fal-ai/stable-audio"


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


@pytest.mark.noci
def test_chat_completions_local_id_surfaces_in_messages_list(
    integration_client: TestClient, agent_ids_to_cleanup
):
    lid = f"e2e-local-{uuid.uuid4().hex[:12]}"
    agent_id = integration_client.create_agent(
        name="LocalId E2E Agent",
        gender="MALE",
        visibility="PUBLIC",
    )
    agent_ids_to_cleanup.append(agent_id)
    integration_client.chat_completions(
        agent_id,
        [{"role": "user", "content": "local id e2e ping"}],
        local_id=lid,
    )
    data = integration_client.get_agent_chat_messages(
        agent_id, limit=20, offset=0, include_festival_memory=False
    )
    msgs = data.get("messages") or []
    matches = [
        m
        for m in msgs
        if m.get("role") == "user"
        and m.get("local_id") == lid
        and (m.get("meta_data") or {}).get("localId") == lid
    ]
    assert len(matches) >= 1


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
