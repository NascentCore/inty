"""Integration tests for chat endpoints using the custom TestClient."""

import asyncio
import json
import threading
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import uuid as uuid_module

import pytest
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient as FastAPITestClient
from jose import jwt
from loguru import logger
from sqlalchemy import create_engine, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.api.v1.endpoints import chat as chat_v1
from app.api.v1.endpoints import chat_ws as chat_ws_v1
from app.core.agent import agent as agent_module
from app.core.companion_harness.companion.llm_inference_errors import (
    CompanionLLMInferenceBackendError,
)
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.config import global_config_loaded_from_config_yaml
from app.core.uuid import get_new_user_id
from app.models.chat_history import ChatHistory
from app.models.memory import Memory
from app.models.user import AuthType, User as UserModel
from app.schemas.chat import ChatMusicGenerationResponse
from app.schemas.response import (
    APIResponse,
    BizError,
    BusinessErrorCode,
    UsageLimitExceeded,
)
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.voice_service import (
    VoiceGenerationResult,
    voice_service as global_voice_service,
)
from app.services import companion_chat_service
from app.services.global_services import (
    subscription_service as global_subscription_service,
)
from app.utils.models_catalog import GenAIModel
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


def _cleanup_chat_history_session(db_session, session_id: str) -> None:
    db_session.execute(
        delete(ChatHistory).where(
            ChatHistory.session_id == uuid_module.UUID(session_id)
        )
    )
    db_session.commit()


@pytest.fixture
def chat_app_with_postgres_db(db_session):
    """
    Chat router with real async Postgres (config.yaml :5432, same as CI).

    Yields (app, user_id, db_session).
    """
    user_id = get_new_user_id()
    device_id = f"test-chat-ws-{uuid_module.uuid4().hex}"
    db_session.add(
        UserModel(
            id=user_id,
            auth_type=AuthType.GOOGLE,
            device_id=device_id,
        )
    )
    db_session.commit()

    _db = global_config_loaded_from_config_yaml.database
    async_engine = create_async_engine(
        str(_db.async_url),
        pool_size=1,
        max_overflow=0,
    )
    async_session_factory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_async_db():
        async with async_session_factory() as session:
            yield session

    app = FastAPI()
    app.include_router(chat_v1.router, prefix="/api/v1")
    app.include_router(chat_ws_v1.router, prefix="/api/v1/chat")
    app.dependency_overrides[deps.get_async_db] = override_get_async_db

    try:
        yield app, user_id, db_session
    finally:
        app.dependency_overrides.clear()
        user_row = db_session.get(UserModel, user_id)
        if user_row is not None:
            db_session.delete(user_row)
            db_session.commit()


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
    app.include_router(chat_ws_v1.router, prefix="/api/v1/chat")

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
            voice_id=None,
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
            captured["client_local_message_id"] = kwargs.get("client_local_message_id")
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
            voice_id=None,
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
            voice_id=None,
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
        return ChatMusicGenerationResponse(
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
    body = response.json()
    assert body["data"]["local_id"] == "guest-limit-local-1"
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
        c for c in choices if c.get("message", {}).get("type") == "premium_preview"
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
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["local_id"] == "temp-client-1"
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


def _setup_companion_ws_chat_test_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    agent_id: str,
    chat_id: str,
    latest_user_message_db_id: int,
    ai_message_id: int,
    run_companion_chat_turn_for_api,
    user_message_save_log: list | None = None,
    ai_message_meta_captures: list | None = None,
) -> None:
    companion_chat_service.clear_companion_chat_service_caches()

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id, **_kwargs):
        return SimpleNamespace(id=chat_id, agent_id=agent_id)

    async def fake_get_agent_for_chat(db, agent_id=None, **_kwargs):
        return {"id": agent_id, "voice_id": "voice-1", "gender": "FEMALE"}

    class DummyAgent:
        async def chat(self, *args, **kwargs):
            return ("legacy-unused", 1)

    async def fake_get_agent(agent_data):
        return DummyAgent()

    async def fake_check_chat_limit(db, user):
        return True, 0, 100

    async def fake_get_user_current_subscription(db, user_id):
        return None

    async def fake_get_or_create_chat_settings(db, cid, user_id, aid):
        return SimpleNamespace(
            voice_enabled=False,
            voice_id=None,
            style_prompt=None,
            premium_mode=False,
            language="en",
        )

    async def fake_record_usage(*args, **kwargs):
        return None

    async def fake_add_user_message_async(session_id, message, meta_data=None):
        if user_message_save_log is not None:
            user_message_save_log.append((session_id, message, meta_data))
        return None

    async def fake_add_ai_message_sync_async(
        session_id, message, meta_data=None, **_kwargs
    ):
        if ai_message_meta_captures is not None and meta_data is not None:
            ai_message_meta_captures.append(meta_data)
        return ai_message_id

    async def fake_get_ai_message_info_by_id(db, message_id):
        md = {}
        if ai_message_meta_captures is not None and ai_message_meta_captures:
            md = dict(ai_message_meta_captures[-1])
        return {
            "id": message_id,
            "meta_data": md,
            "timestamp": 1735689600000,
            "audio_url": None,
        }

    async def fake_get_latest_user_message_id(db, session_id):
        return latest_user_message_db_id

    async def fake_get_latest_ai_message_info(db, session_id):
        return None

    async def fake_mark_user_push_notifications_as_read(db, user_id):
        return 0

    async def fake_try_trigger_surprise_snap(db, session_id, user_id, aid):
        return None

    for attr in (
        "run_companion_user_chat_turn_for_api",
        "run_companion_implicit_sign_on_greeting_turn_for_api",
        "run_companion_chat_turn_for_api",
    ):
        monkeypatch.setattr(
            companion_chat_service,
            attr,
            run_companion_chat_turn_for_api,
        )
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
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "record_usage",
        fake_record_usage,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_user_message_async",
        fake_add_user_message_async,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_ai_message_sync_async",
        fake_add_ai_message_sync_async,
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
        chat_history_service,
        "get_latest_ai_message_info",
        fake_get_latest_ai_message_info,
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

    user = _make_user(auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    async def fake_agent_status_line(db, agent_id):
        return None

    monkeypatch.setattr(
        chat_ws_v1,
        "_agent_status_line_for_chat_header",
        fake_agent_status_line,
    )


def _setup_companion_ws_chat_test_env_with_postgres(
    monkeypatch: pytest.MonkeyPatch,
    *,
    user_id: str,
    agent_id: str,
    chat_id: str,
    run_companion_chat_turn_for_api,
) -> str:
    """
    Companion WS stubs with real chat_history persistence on Postgres.

    Returns session_id used for chat_history rows (for teardown).
    """
    companion_chat_service.clear_companion_chat_service_caches()
    session_id = generate_session_id(chat_id)

    async def fake_get_or_create_chat_by_agent(
        db, user_id=None, agent_id=None, **_kwargs
    ):
        _ = user_id
        return SimpleNamespace(id=chat_id, agent_id=agent_id)

    async def fake_get_agent_for_chat(db, agent_id=None, **_kwargs):
        return {"id": agent_id, "voice_id": "voice-1", "gender": "FEMALE"}

    async def fake_get_or_create_chat_settings(
        db, chat_id_arg, user_id=None, agent_id=None, **_kwargs
    ):
        _ = (chat_id_arg, user_id, agent_id)
        return SimpleNamespace(
            voice_enabled=False,
            voice_id=None,
            style_prompt=None,
            premium_mode=False,
            language="en",
        )

    async def fake_get_user_current_subscription(db, user_id, **_kwargs):
        _ = user_id
        return None

    async def fake_record_usage(*args, **kwargs):
        return None

    async def fake_mark_user_push_notifications_as_read(db, uid):
        return 0

    async def fake_try_trigger_surprise_snap(db, session_id, uid, aid):
        return None

    for attr in (
        "run_companion_user_chat_turn_for_api",
        "run_companion_implicit_sign_on_greeting_turn_for_api",
        "run_companion_chat_turn_for_api",
    ):
        monkeypatch.setattr(
            companion_chat_service,
            attr,
            run_companion_chat_turn_for_api,
        )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(agent_service, "get_agent_for_chat", fake_get_agent_for_chat)
    monkeypatch.setattr(
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "record_usage",
        fake_record_usage,
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

    test_user = _make_user(user_id=user_id, auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return test_user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    async def fake_agent_status_line(db, aid):
        return None

    monkeypatch.setattr(
        chat_ws_v1,
        "_agent_status_line_for_chat_header",
        fake_agent_status_line,
    )
    return session_id


def test_chat_completions_companion_kernel_branch_writes_history(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    """POST completions always uses legacy Agent (companion kernel is WebSocket-only)."""
    companion_chat_service.clear_companion_chat_service_caches()

    captured: dict = {"companion_calls": 0}

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["companion_calls"] += 1
        return CompanionTurnResult(assistant_text="companion-reply-xyz")

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-42", agent_id=agent_id)

    async def fake_get_agent_for_chat(db, agent_id):
        return {"id": agent_id, "voice_id": "voice-1", "gender": "FEMALE"}

    class DummyAgent:
        async def chat(self, *args, **kwargs):
            captured["agent_chat_called"] = True
            return ("legacy-from-agent", 902)

    async def fake_get_agent(agent_data):
        return DummyAgent()

    async def fake_check_chat_limit(db, user):
        return True, 0, 100

    async def fake_get_user_current_subscription(db, user_id):
        return None

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            voice_enabled=False,
            voice_id=None,
            style_prompt=None,
            premium_mode=False,
            language="en",
        )

    async def fake_record_usage(*args, **kwargs):
        return None

    async def fake_add_user_message_async(session_id, message, meta_data=None):
        captured["user_save"] = (session_id, message, meta_data)
        return None

    async def fake_add_ai_message_sync_async(
        session_id, message, agent_id=None, meta_data=None
    ):
        captured["ai_save"] = (session_id, message, agent_id, meta_data)
        return 901

    async def fake_get_ai_message_info_by_id(db, message_id):
        return {
            "id": message_id,
            "meta_data": {},
            "timestamp": 1735689600000,
            "audio_url": None,
        }

    async def fake_get_latest_user_message_id(db, session_id):
        return 55

    async def fake_get_latest_ai_message_info(db, session_id):
        return None

    async def fake_mark_user_push_notifications_as_read(db, user_id):
        return 0

    async def fake_try_trigger_surprise_snap(db, session_id, user_id, agent_id):
        return None

    monkeypatch.setattr(
        companion_chat_service,
        "run_companion_chat_turn_for_api",
        fake_run_companion_chat_turn_for_api,
    )
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
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "record_usage",
        fake_record_usage,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_user_message_async",
        fake_add_user_message_async,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_ai_message_sync_async",
        fake_add_ai_message_sync_async,
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
        chat_history_service,
        "get_latest_ai_message_info",
        fake_get_latest_ai_message_info,
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

    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {"messages": [{"role": "user", "content": "hello kernel"}]}
    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chat/completions/agent-companion-1", json=payload
        )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 200
    assert body["data"]["choices"][0]["message"]["content"] == "legacy-from-agent"
    assert captured["companion_calls"] == 0
    assert captured.get("agent_chat_called") is True

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_kernel_branch_writes_history(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    """WebSocket /api/v1/chat/ws always uses companion kernel (same stubs as HTTP path)."""
    companion_chat_service.clear_companion_chat_service_caches()

    captured: dict = {
        "companion_calls": 0,
        "preset_user_msg_uuids": [],
        "ai_metas": [],
    }

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["companion_calls"] += 1
        captured["preset_user_msg_uuids"].append(kwargs.get("preset_user_msg_uuid"))
        n = captured["companion_calls"]
        uid = str(kwargs.get("preset_user_msg_uuid") or "")
        return CompanionTurnResult(
            assistant_text="companion-ws-reply",
            user_msg_uuid=uid,
            assistant_msg_uuid=f"33333333-3333-4333-8333-{n:012d}",
            significance_perception={
                "importance_round": 9,
                "importance_user_message": 8,
                "importance_assistant_message": 7,
            },
        )

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-ws-1", agent_id=agent_id)

    async def fake_get_agent_for_chat(db, agent_id):
        return {"id": agent_id, "voice_id": "voice-1", "gender": "FEMALE"}

    class DummyAgent:
        async def chat(self, *args, **kwargs):
            captured["agent_chat_called"] = True
            return ("should-not-use", 1)

    async def fake_get_agent(agent_data):
        return DummyAgent()

    async def fake_check_chat_limit(db, user):
        return True, 0, 100

    async def fake_get_user_current_subscription(db, user_id):
        return None

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            voice_enabled=False,
            voice_id=None,
            style_prompt=None,
            premium_mode=False,
            language="en",
        )

    async def fake_record_usage(*args, **kwargs):
        return None

    async def fake_add_user_message_async(session_id, message, meta_data=None):
        captured["user_save"] = (session_id, message, meta_data)
        return None

    async def fake_add_ai_message_sync_async(
        session_id, message, agent_id=None, meta_data=None
    ):
        captured["ai_save"] = (session_id, message, agent_id, meta_data)
        if meta_data is not None:
            captured["last_ai_meta"] = dict(meta_data)
            captured["ai_metas"].append(dict(meta_data))
        else:
            captured["last_ai_meta"] = {}
        return 903

    async def fake_get_ai_message_info_by_id(db, message_id):
        return {
            "id": message_id,
            "meta_data": dict(captured.get("last_ai_meta") or {}),
            "timestamp": 1735689600000,
            "audio_url": None,
        }

    async def fake_get_latest_user_message_id(db, session_id):
        return 56

    async def fake_get_latest_ai_message_info(db, session_id):
        return None

    async def fake_mark_user_push_notifications_as_read(db, user_id):
        return 0

    async def fake_try_trigger_surprise_snap(db, session_id, user_id, agent_id):
        return None

    for attr in (
        "run_companion_user_chat_turn_for_api",
        "run_companion_implicit_sign_on_greeting_turn_for_api",
        "run_companion_chat_turn_for_api",
    ):
        monkeypatch.setattr(
            companion_chat_service,
            attr,
            fake_run_companion_chat_turn_for_api,
        )
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
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "record_usage",
        fake_record_usage,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_user_message_async",
        fake_add_user_message_async,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_ai_message_sync_async",
        fake_add_ai_message_sync_async,
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
        chat_history_service,
        "get_latest_ai_message_info",
        fake_get_latest_ai_message_info,
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

    user = _make_user(auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    async def fake_agent_status_line(db, agent_id):
        return None

    monkeypatch.setattr(
        chat_ws_v1,
        "_agent_status_line_for_chat_header",
        fake_agent_status_line,
    )

    first_turn_uuid = "11111111-1111-4111-8111-111111111111"
    second_turn_uuid = "01234567-89ab-cdef-0123-456789abcdef"

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-ws",
                    "request": {
                        "messages": [{"role": "user", "content": "hello ws kernel"}],
                        "message_id": first_turn_uuid,
                    },
                }
            )
            body = websocket.receive_json()
            websocket.send_json(
                {
                    "agent_id": "agent-companion-ws",
                    "request": {
                        "messages": [{"role": "user", "content": "second turn"}],
                        "message_id": second_turn_uuid,
                    },
                }
            )
            body2 = websocket.receive_json()

    assert body["code"] == 200
    assert body["agent_id"] == "agent-companion-ws"
    assert body["data"]["choices"][0]["message"]["content"] == "companion-ws-reply"
    assert body2["code"] == 200
    assert captured["companion_calls"] == 2
    assert captured["preset_user_msg_uuids"][0] == first_turn_uuid
    assert captured["preset_user_msg_uuids"][1] == second_turn_uuid
    assert captured.get("agent_chat_called") is not True
    assert captured["ai_save"][1] == "companion-ws-reply"
    assert captured["ai_save"][3] == {
        "source": "chat",
        "user_msg_uuid": second_turn_uuid,
        "assistant_msg_uuid": "33333333-3333-4333-8333-000000000002",
        "significance_perception": {
            "importance_round": 9,
            "importance_user_message": 8,
            "importance_assistant_message": 7,
        },
    }
    assert body["data"]["choices"][0]["message"]["meta_data"] == captured["ai_metas"][0]
    assert (
        body2["data"]["choices"][0]["message"]["meta_data"] == captured["ai_metas"][1]
    )

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_foreground_tool_background_started_meta(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    ai_meta: list = []

    async def fake_run_companion_chat_turn_for_api(**_kwargs):
        return CompanionTurnResult(
            assistant_text="tb-reply",
            tool_background_started=True,
        )

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-tbgs",
        chat_id="chat-tbgs-1",
        latest_user_message_db_id=91,
        ai_message_id=905,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
        ai_message_meta_captures=ai_meta,
    )

    msg_uuid = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-tbgs",
                    "request": {
                        "messages": [{"role": "user", "content": "paint"}],
                        "message_id": msg_uuid,
                    },
                }
            )
            body = websocket.receive_json()

    assert body["code"] == 200
    assert ai_meta[-1]["tool_background_started"] is True
    assert (
        body["data"]["choices"][0]["message"]["meta_data"]["tool_background_started"]
        is True
    )

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_llm_inference_backend_error_frame(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    """When the companion kernel reports an upstream LLM API failure, the client gets a tagged error frame."""

    async def fake_run_companion(**_kwargs):
        raise CompanionLLMInferenceBackendError(
            client_message_en=(
                "The AI inference provider rejected this request due to insufficient credits, quota, "
                "or token limits on the service side. Please try again later."
            ),
            provider_http_status=402,
        )

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-llm-err",
        chat_id="chat-llm-err-1",
        latest_user_message_db_id=57,
        ai_message_id=904,
        run_companion_chat_turn_for_api=fake_run_companion,
    )

    msg_uuid = "22222222-2222-4222-8222-222222222222"
    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-llm-err",
                    "request": {
                        "messages": [{"role": "user", "content": "hello"}],
                        "message_id": msg_uuid,
                    },
                }
            )
            body = websocket.receive_json()

    assert body["code"] == 502
    assert body["agent_id"] == "agent-companion-llm-err"
    assert body["error_kind"] == "llm_inference_backend"
    assert body["llm_provider_http_status"] == 402
    assert "inference provider" in body["message"].lower()

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_passes_implicit_signal_bundle_with_time_context(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured: dict = {}

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["bundle"] = kwargs.get("implicit_signal_bundle")
        return CompanionTurnResult(assistant_text="ok")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-impl",
        chat_id="chat-impl-1",
        latest_user_message_db_id=90,
        ai_message_id=901,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    msg_uuid = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-impl",
                    "request": {
                        "messages": [{"role": "user", "content": "hi"}],
                        "message_id": msg_uuid,
                        "time_context": {
                            "local_time": "2026-05-01T10:00:00",
                            "timezone": "Europe/Berlin",
                            "utc_offset_minutes": 120,
                        },
                    },
                }
            )
            body = websocket.receive_json()

    assert body["code"] == 200
    bundle = captured["bundle"]
    assert bundle is not None
    assert bundle.schema_version == 1
    assert bundle.client_time is not None
    assert bundle.client_time.local_time == "2026-05-01T10:00:00"
    assert bundle.client_time.timezone == "Europe/Berlin"
    assert bundle.client_time.utc_offset_minutes == 120
    assert bundle.server_received_at_utc is not None
    assert bundle.user_signed_on is False

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_rejects_implicit_user_signed_on_message_type(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured: dict = {"companion_calls": 0}

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["companion_calls"] += 1
        return CompanionTurnResult(assistant_text="should-not-run")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-signon-reject",
        chat_id="chat-signon-reject-1",
        latest_user_message_db_id=90,
        ai_message_id=902,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    msg_uuid = "bbbbbbbb-bbbb-4ccc-dddd-eeeeeeeeeeee"
    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-signon-reject",
                    "request": {
                        "messages": [{"role": "user", "content": ""}],
                        "message_id": msg_uuid,
                        "messageType": "IMPLICIT_USER_SIGNED_ON",
                    },
                }
            )
            body = websocket.receive_json()

    assert body["code"] != 200
    assert captured["companion_calls"] == 0

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_user_signed_on_greeting_sets_bundle(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured: dict = {}
    user_saves: list = []

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["bundle"] = kwargs.get("implicit_signal_bundle")
        return CompanionTurnResult(assistant_text="greet-cf")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-signon-cf",
        chat_id="chat-signon-cf-1",
        latest_user_message_db_id=90,
        ai_message_id=910,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
        user_message_save_log=user_saves,
    )

    msg_uuid = "aaaaaaaa-bbbb-4ccc-dddd-999999999999"
    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "user_signed_on",
                    "agent_id": "agent-companion-signon-cf",
                    "message_id": msg_uuid,
                }
            )
            body = websocket.receive_json()
            if body.get("type") == "user_signed_on_ack":
                body = websocket.receive_json()

    assert body["code"] == 200
    bundle = captured["bundle"]
    assert bundle is not None
    assert bundle.user_signed_on is True
    assert user_saves == []

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_user_signed_on_greeting_cancelled_on_disconnect(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    """Regression: detached greeting turn is cancelled when the WebSocket session ends."""
    turn_started = threading.Event()
    turn_completed = threading.Event()

    async def slow_run_companion_chat_turn_for_api(**_kwargs):
        turn_started.set()
        await asyncio.sleep(60.0)
        turn_completed.set()
        return CompanionTurnResult(assistant_text="never")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-signon-cancel",
        chat_id="chat-signon-cancel-1",
        latest_user_message_db_id=91,
        ai_message_id=911,
        run_companion_chat_turn_for_api=slow_run_companion_chat_turn_for_api,
    )

    msg_uuid = "bbbbbbbb-bbbb-4bbb-bbbb-aaaaaaaaaaaa"
    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "user_signed_on",
                    "agent_id": "agent-companion-signon-cancel",
                    "message_id": msg_uuid,
                }
            )
            ack = websocket.receive_json()
            assert ack["type"] == "user_signed_on_ack"
            assert ack["ok"] is True
            assert turn_started.wait(timeout=2.0)

    time.sleep(0.15)
    assert not turn_completed.is_set()

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_inner_tick_worker_stops_after_disconnect(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    """Regression: ``companion_ws_inner_tick`` task is cancelled in ``finally``; no further polls."""
    ticks: dict[str, int] = {"proactive": 0, "maintenance": 0, "scheduled": 0}

    async def spy_scheduled(**_kwargs):
        ticks["scheduled"] += 1

    async def spy_proactive(**_kwargs):
        ticks["proactive"] += 1

    async def spy_maintenance(**_kwargs):
        ticks["maintenance"] += 1

    async def fake_run_companion_chat_turn_for_api(**_kwargs):
        return CompanionTurnResult(assistant_text="unused")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-inner-tick-stop",
        chat_id="chat-inner-tick-stop-1",
        latest_user_message_db_id=501,
        ai_message_id=9501,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    monkeypatch.setattr(
        global_config_loaded_from_config_yaml.app.features,
        "companion_ws_proactive_chat_poll_seconds",
        0.05,
    )
    from app.services.agentic_companion import inner_tick_fire as inner_tick_fire_mod

    monkeypatch.setattr(
        inner_tick_fire_mod,
        "try_fire_scheduled_inner_tick",
        spy_scheduled,
    )
    monkeypatch.setattr(
        inner_tick_fire_mod,
        "try_fire_proactive_chat_inner_tick",
        spy_proactive,
    )
    monkeypatch.setattr(
        inner_tick_fire_mod,
        "try_fire_maintenance_inner_tick",
        spy_maintenance,
    )

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "user_signed_on",
                    "agent_id": "agent-companion-inner-tick-stop",
                    "message_id": "cccccccc-cccc-4ccc-dddd-eeeeeeeeeeee",
                }
            )
            ack = websocket.receive_json()
            assert ack["type"] == "user_signed_on_ack"
            assert ack["ok"] is True
            time.sleep(0.2)
            assert (
                ticks["proactive"] + ticks["maintenance"] + ticks["scheduled"] >= 1
            )

    n_at_close = ticks["proactive"] + ticks["maintenance"] + ticks["scheduled"]
    time.sleep(0.35)
    assert ticks["proactive"] + ticks["maintenance"] + ticks["scheduled"] == n_at_close

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_inner_tick_scheduled_when_coords_disarmed(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    """Scheduled reminder runs when armed; proactive skips after user_signed_out disarms coords."""
    ticks = {"scheduled": 0, "proactive": 0}

    async def spy_scheduled(**_kwargs):
        ticks["scheduled"] += 1

    async def spy_proactive(**_kwargs):
        ticks["proactive"] += 1

    async def spy_maintenance(**_kwargs):
        raise AssertionError("maintenance should not run when disabled")

    async def fake_run_companion_chat_turn_for_api(**_kwargs):
        return CompanionTurnResult(assistant_text="unused")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-inner-tick-sched",
        chat_id="chat-inner-tick-sched-1",
        latest_user_message_db_id=502,
        ai_message_id=9502,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    monkeypatch.setattr(
        global_config_loaded_from_config_yaml.app.features,
        "companion_ws_proactive_chat_poll_seconds",
        0.05,
    )
    monkeypatch.setattr(
        global_config_loaded_from_config_yaml.app.features,
        "companion_ws_maintenance_inner_tick_enabled",
        False,
    )
    from app.services.agentic_companion import inner_tick_fire as inner_tick_fire_mod

    monkeypatch.setattr(
        inner_tick_fire_mod,
        "try_fire_scheduled_inner_tick",
        spy_scheduled,
    )
    monkeypatch.setattr(
        inner_tick_fire_mod,
        "try_fire_proactive_chat_inner_tick",
        spy_proactive,
    )
    monkeypatch.setattr(
        inner_tick_fire_mod,
        "try_fire_maintenance_inner_tick",
        spy_maintenance,
    )

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "user_signed_on",
                    "agent_id": "agent-companion-inner-tick-sched",
                    "message_id": "dddddddd-dddd-4ddd-eeee-ffffffffffff",
                }
            )
            ack = websocket.receive_json()
            assert ack["type"] == "user_signed_on_ack"
            assert ack["ok"] is True
            time.sleep(0.2)
            assert ticks["scheduled"] >= 1
            assert ticks["proactive"] >= 1
            websocket.send_json(
                {
                    "type": "user_signed_out",
                    "agent_id": "agent-companion-inner-tick-sched",
                    "message_id": "eeeeeeee-eeee-4eee-ffff-eeeeeeeeeeee",
                }
            )
            out_ack = None
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                msg = websocket.receive_json()
                if msg.get("type") == "user_signed_out_ack":
                    out_ack = msg
                    break
            assert out_ack is not None
            assert out_ack.get("ok") is True
            ticks["proactive"] = 0
            time.sleep(0.2)
            assert ticks["proactive"] == 0

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_user_signed_on_missing_message_id(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    async def fake_run_companion_chat_turn_for_api(**kwargs):
        raise AssertionError("companion should not run without message_id")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-signon-cf-mid",
        chat_id="chat-signon-cf-mid-1",
        latest_user_message_db_id=90,
        ai_message_id=911,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "user_signed_on",
                    "agent_id": "agent-companion-signon-cf-mid",
                }
            )
            ack = websocket.receive_json()

    assert ack["type"] == "user_signed_on_ack"
    assert ack["ok"] is False
    assert ack["reason"] == "missing_message_id"

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_user_signed_on_invalid_message_id(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    async def fake_run_companion_chat_turn_for_api(**kwargs):
        raise AssertionError("companion should not run with bad message_id")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-signon-cf-badmid",
        chat_id="chat-signon-cf-badmid-1",
        latest_user_message_db_id=90,
        ai_message_id=912,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "user_signed_on",
                    "agent_id": "agent-companion-signon-cf-badmid",
                    "message_id": "not-a-uuid",
                }
            )
            ack = websocket.receive_json()

    assert ack["type"] == "user_signed_on_ack"
    assert ack["ok"] is False
    assert ack["reason"] == "invalid_message_id"

    companion_chat_service.clear_companion_chat_service_caches()


def test_v1_chat_completions_http_rejects_removed_implicit_user_signed_on_message_type(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    _stub_chat_completion_dependencies(monkeypatch)
    user = _make_user(auth_type=AuthType.GOOGLE)
    payload = {
        "messages": [{"role": "user", "content": ""}],
        "stream": False,
        "model": "chatbot",
        "language": "zh",
        "messageType": "IMPLICIT_USER_SIGNED_ON",
    }
    with _client_with_user(chat_business_error_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)
    assert response.status_code == 422

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_rejects_multimodal_image_user_turn(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured: dict = {"companion_calls": 0}

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["companion_calls"] += 1
        return CompanionTurnResult(assistant_text="should-not-run")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-mm",
        chat_id="chat-mm-1",
        latest_user_message_db_id=57,
        ai_message_id=1,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-mm",
                    "request": {
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "caption"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": "https://example.com/x.png"
                                        },
                                    },
                                ],
                            }
                        ],
                    },
                }
            )
            body = websocket.receive_json()

    assert body["code"] == 400
    assert "Multimodal" in body["message"]
    assert captured["companion_calls"] == 0

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_rejects_missing_message_id(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured: dict = {"companion_calls": 0}

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["companion_calls"] += 1
        return CompanionTurnResult(assistant_text="should-not-run")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-mid",
        chat_id="chat-mid-1",
        latest_user_message_db_id=59,
        ai_message_id=1,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-mid",
                    "request": {
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                }
            )
            body = websocket.receive_json()

    assert body["code"] == 400
    assert "message_id" in body["message"]
    assert captured["companion_calls"] == 0

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_rejects_non_uuid_message_id(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured: dict = {"companion_calls": 0}

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["companion_calls"] += 1
        return CompanionTurnResult(assistant_text="should-not-run")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-mid2",
        chat_id="chat-mid-2",
        latest_user_message_db_id=60,
        ai_message_id=1,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-mid2",
                    "request": {
                        "messages": [{"role": "user", "content": "hi"}],
                        "message_id": "local-optimistic-123",
                    },
                }
            )
            body = websocket.receive_json()

    assert body["code"] == 400
    assert "UUID" in body["message"]
    assert captured["companion_calls"] == 0

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_companion_accepts_text_only_multipart_user_turn(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured: dict = {"companion_calls": 0}

    async def fake_run_companion_chat_turn_for_api(**kwargs):
        captured["companion_calls"] += 1
        assert kwargs["user_text"] == "a\nb"
        return CompanionTurnResult(assistant_text="ok-parts")

    _setup_companion_ws_chat_test_env(
        monkeypatch,
        agent_id="agent-companion-txtparts",
        chat_id="chat-txtparts-1",
        latest_user_message_db_id=58,
        ai_message_id=904,
        run_companion_chat_turn_for_api=fake_run_companion_chat_turn_for_api,
    )

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "agent_id": "agent-companion-txtparts",
                    "request": {
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "a"},
                                    {"type": "text", "text": "b"},
                                ],
                            }
                        ],
                        "message_id": "22222222-2222-4222-8222-222222222222",
                    },
                }
            )
            body = websocket.receive_json()

    assert body["code"] == 200
    assert body["data"]["choices"][0]["message"]["content"] == "ok-parts"
    assert captured["companion_calls"] == 1

    companion_chat_service.clear_companion_chat_service_caches()


def test_chat_websocket_reuses_connection_for_multiple_agents(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    user = _make_user(auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    async def fake_agent_chat_ws_completions(
        *,
        db,
        agent_id,
        request,
        current_user,
        subscription_svc,
        voice_svc=None,
        companion_background_sink=None,
        companion_ws_foreground_pending=None,
        companion_ws_inner_tick_ctx=None,
        companion_ws=None,
        implicit_greeting_turn=False,
        ws_outbound_queue=None,
    ):
        return APIResponse.success(
            data={
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"reply:{agent_id}",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "source_imate_id": request.target_imate_id,
            }
        ).model_dump(exclude_none=True)

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)
    monkeypatch.setattr(
        chat_ws_v1, "_agent_chat_ws_completions_impl", fake_agent_chat_ws_completions
    )

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

    async def fake_agent_chat_ws_completions(**kwargs):
        return APIResponse.success(data={"choices": []}).model_dump(exclude_none=True)

    expected_idle = float(
        global_config_loaded_from_config_yaml.app.features.chat_ws_idle_timeout_seconds
    )
    real_wait_for = chat_ws_v1.asyncio.wait_for

    async def fake_wait_for(aw, timeout):
        if float(timeout) != expected_idle:
            return await real_wait_for(aw, timeout)
        # Only count idle waits wrapping ``WebSocket.receive_text``; the companion
        # inner-tick worker also uses ``asyncio.wait_for`` with the same poll
        # interval when both YAML values match ``chat_ws_idle_timeout_seconds``.
        code = getattr(aw, "cr_code", None)
        if code is None or code.co_name != "receive_text":
            return await real_wait_for(aw, timeout)
        captured["timeouts"].append(timeout)
        if len(captured["timeouts"]) == 1:
            return await aw
        raise asyncio.TimeoutError()

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)
    monkeypatch.setattr(
        chat_ws_v1, "_agent_chat_ws_completions_impl", fake_agent_chat_ws_completions
    )
    monkeypatch.setattr(chat_ws_v1.asyncio, "wait_for", fake_wait_for)

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

    async def fake_agent_chat_ws_completions(
        *,
        db,
        agent_id,
        request,
        current_user,
        subscription_svc,
        voice_svc=None,
        companion_background_sink=None,
        companion_ws_foreground_pending=None,
        companion_ws_inner_tick_ctx=None,
        companion_ws=None,
        implicit_greeting_turn=False,
        ws_outbound_queue=None,
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
        ).model_dump(exclude_none=True)

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)
    monkeypatch.setattr(
        chat_ws_v1, "_agent_chat_ws_completions_impl", fake_agent_chat_ws_completions
    )

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

    async def fake_agent_chat_ws_completions(
        *,
        db,
        agent_id,
        request,
        current_user,
        subscription_svc,
        voice_svc=None,
        companion_background_sink=None,
        companion_ws_foreground_pending=None,
        companion_ws_inner_tick_ctx=None,
        companion_ws=None,
        implicit_greeting_turn=False,
        ws_outbound_queue=None,
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
        ).model_dump(exclude_none=True)

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)
    monkeypatch.setattr(
        chat_ws_v1, "_agent_chat_ws_completions_impl", fake_agent_chat_ws_completions
    )

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
            assert websocket.receive_json() == {
                "type": "client_context_ack",
                "ok": True,
            }
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


def test_chat_websocket_user_signed_out_appends_ws_runtime_event(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    import time

    captured: dict[str, object] = {}

    def fake_append(**kwargs):
        captured["kwargs"] = kwargs

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id=42, agent_id=agent_id)

    async def fake_get_user_current_subscription(db, user_id):
        return None

    monkeypatch.setattr(
        companion_chat_service,
        "append_companion_ws_runtime_event",
        fake_append,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )

    user = _make_user(user_id="user-so-1", auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    msg_uuid = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "user_signed_out",
                    "agent_id": "agent-so-1",
                    "message_id": msg_uuid,
                }
            )
            ack = websocket.receive_json()

    assert ack == {"type": "user_signed_out_ack", "ok": True}
    deadline = time.monotonic() + 2.0
    while "kwargs" not in captured and time.monotonic() < deadline:
        time.sleep(0.01)
    assert "kwargs" in captured, "append_companion_ws_runtime_event should run after ack"
    kw = captured["kwargs"]
    assert kw["user_id"] == "user-so-1"
    assert kw["agent_id"] == "agent-so-1"
    assert kw["chat_id"] == 42
    assert isinstance(kw["resolved_chat_model"], GenAIModel)
    assert kw["resolved_chat_model"].id_on_provider
    record = kw["record"]
    assert isinstance(record, dict)
    assert record["kind"] == "user_signed_out"
    assert record["user_id"] == "user-so-1"
    assert record["agent_id"] == "agent-so-1"
    assert record["chat_id"] == "42"
    assert record["received_message_uuid"] == msg_uuid


def test_chat_websocket_verify_user_signed_out_not_supported(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    user = _make_user(auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws/verify") as websocket:
            websocket.send_json({"type": "user_signed_out", "agent_id": "agent-v"})
            ack = websocket.receive_json()

    assert ack == {
        "type": "user_signed_out_ack",
        "ok": False,
        "reason": "not_supported",
    }


def test_is_ws_receive_text_not_connected_runtime_error() -> None:
    assert chat_ws_v1._is_ws_receive_text_not_connected_runtime_error(
        RuntimeError(chat_ws_v1._WS_RECEIVE_TEXT_NOT_CONNECTED_MSG)
    )
    assert not chat_ws_v1._is_ws_receive_text_not_connected_runtime_error(
        RuntimeError("other")
    )
    assert not chat_ws_v1._is_ws_receive_text_not_connected_runtime_error(
        WebSocketDisconnect()
    )


def test_chat_websocket_verify_receive_text_not_connected_runtime_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
) -> None:
    user = _make_user(auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    async def boom_receive_text(self):
        raise RuntimeError(chat_ws_v1._WS_RECEIVE_TEXT_NOT_CONNECTED_MSG)

    monkeypatch.setattr(WebSocket, "receive_text", boom_receive_text)

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws/verify"):
            pass


def test_chat_websocket_recv_not_connected_runtime_after_ping_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
) -> None:
    """``recv_task.result()`` Starlette ``RuntimeError`` must not crash the ASGI app."""
    user = _make_user(user_id="user-ws-nc-runtime", auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    async def boom_receive_text(self):
        raise RuntimeError(chat_ws_v1._WS_RECEIVE_TEXT_NOT_CONNECTED_MSG)

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws?ws_conn_id=aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee") as websocket:
            websocket.send_json({"type": "ping"})
            assert websocket.receive_json() == {"type": "pong"}
            monkeypatch.setattr(WebSocket, "receive_text", boom_receive_text)
            websocket.send_json({"type": "ping"})


def test_chat_websocket_session_open_uses_client_ws_conn_id_query(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    client_ws = "11111111-2222-4333-8444-555555555555"
    expected_norm = str(uuid.UUID(client_ws))
    session_open_msgs: list[str] = []

    def _sink(message):
        rec = message.record
        msg = rec["message"]
        if "chat_ws session_open" in msg:
            session_open_msgs.append(msg)

    hid = logger.add(_sink, level="INFO")
    try:
        user = _make_user(user_id="user-ws-cid-1", auth_type=AuthType.GOOGLE)

        async def fake_ws_user(websocket, db):
            return user

        monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)
        with FastAPITestClient(chat_business_error_app) as client:
            path = f"/api/v1/chat/ws?ws_conn_id={client_ws}"
            with client.websocket_connect(path) as websocket:
                websocket.send_json({"type": "ping"})
                assert websocket.receive_json() == {"type": "pong"}
    finally:
        logger.remove(hid)

    assert session_open_msgs
    assert any(expected_norm in m for m in session_open_msgs), session_open_msgs


def test_chat_websocket_invalid_ws_conn_id_query_logs_fallback(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    invalid_msgs: list[str] = []
    session_open_msgs: list[str] = []

    def _sink(message):
        rec = message.record
        msg = rec["message"]
        if "ws_conn_id_query_invalid" in msg:
            invalid_msgs.append(msg)
        if "chat_ws session_open" in msg:
            session_open_msgs.append(msg)

    hid = logger.add(_sink, level="INFO")
    try:
        user = _make_user(user_id="user-ws-cid-2", auth_type=AuthType.GOOGLE)

        async def fake_ws_user(websocket, db):
            return user

        monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)
        with FastAPITestClient(chat_business_error_app) as client:
            with client.websocket_connect(
                "/api/v1/chat/ws?ws_conn_id=not-a-valid-uuid"
            ) as websocket:
                websocket.send_json({"type": "ping"})
                assert websocket.receive_json() == {"type": "pong"}
    finally:
        logger.remove(hid)

    assert invalid_msgs
    assert any("not-a-valid-uuid" in m for m in invalid_msgs), invalid_msgs
    assert session_open_msgs
    assert not any("not-a-valid-uuid" in m for m in session_open_msgs), session_open_msgs


def test_chat_websocket_ws_conn_dropped_appends_ws_runtime_event(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    captured: dict[str, object] = {}

    def fake_append(**kwargs):
        captured["kwargs"] = kwargs

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id=42, agent_id=agent_id)

    async def fake_get_user_current_subscription(db, user_id):
        return None

    monkeypatch.setattr(
        companion_chat_service,
        "append_companion_ws_runtime_event",
        fake_append,
    )
    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(
        global_subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )

    user = _make_user(user_id="user-wd-1", auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    msg_uuid = "bbbbbbbb-bbbb-4ccc-dddd-eeeeeeeeeeee"
    dropped_at = "2026-05-11T12:00:00+00:00"
    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "ws_conn_dropped",
                    "agent_id": "agent-wd-1",
                    "dropped_at_utc": dropped_at,
                    "message_id": msg_uuid,
                    "ws_close_code": 1006,
                    "ws_close_reason": "connection reset",
                }
            )
            ack = websocket.receive_json()

    assert ack == {"type": "ws_conn_dropped_ack", "ok": True}
    kw = captured["kwargs"]
    assert kw["user_id"] == "user-wd-1"
    assert kw["agent_id"] == "agent-wd-1"
    assert kw["chat_id"] == 42
    assert isinstance(kw["resolved_chat_model"], GenAIModel)
    assert kw["resolved_chat_model"].id_on_provider
    record = kw["record"]
    assert isinstance(record, dict)
    assert record["kind"] == "ws_conn_dropped"
    assert record["user_id"] == "user-wd-1"
    assert record["agent_id"] == "agent-wd-1"
    assert record["chat_id"] == "42"
    assert record["client_dropped_at_utc"] == dropped_at
    assert record["ws_close_code"] == 1006
    assert record["ws_close_reason"] == "connection reset"
    assert record["received_message_uuid"] == msg_uuid


def test_chat_websocket_verify_ws_conn_dropped_not_supported(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    user = _make_user(auth_type=AuthType.GOOGLE)

    async def fake_ws_user(websocket, db):
        return user

    monkeypatch.setattr(chat_ws_v1, "_get_current_user_from_websocket", fake_ws_user)

    with FastAPITestClient(chat_business_error_app) as client:
        with client.websocket_connect("/api/v1/chat/ws/verify") as websocket:
            websocket.send_json(
                {
                    "type": "ws_conn_dropped",
                    "agent_id": "agent-v",
                    "dropped_at_utc": "2026-05-11T12:00:00+00:00",
                }
            )
            ack = websocket.receive_json()

    assert ack == {
        "type": "ws_conn_dropped_ack",
        "ok": False,
        "reason": "not_supported",
    }


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

    async def fake_produce_voice_for_user(*args, **kwargs):
        captured_voice_id["value"] = kwargs.get("voice_id")
        return (
            VoiceGenerationResult(
                gcs_url="gs://test-bucket/voice/202603/voice_test.wav",
                gcs_http_url="https://storage.googleapis.com/test-bucket/voice/202603/voice_test.wav",
                duration_seconds=1.23,
            ),
            True,
            0,
            10,
        )

    from app.services import chat_assistant_voice

    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(
        chat_assistant_voice,
        "produce_voice_for_user",
        fake_produce_voice_for_user,
    )

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


def test_v1_chat_completions_http_uses_legacy_assistant_voice_not_ws_tts(
    monkeypatch: pytest.MonkeyPatch, chat_business_error_app: FastAPI
):
    """HTTP /api/v1/chat/completions uses synthesize_chat_assistant_audio for legacy voice_enabled TTS."""
    legacy_called: dict[str, bool] = {"value": False}

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

    async def tracking_legacy_synthesize(**kwargs):
        legacy_called["value"] = True
        assert kwargs["voice_enabled"] is True
        return (
            "https://storage.googleapis.com/test-bucket/voice/legacy.wav",
            1.23,
        )

    monkeypatch.setattr(
        chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(
        chat_v1,
        "synthesize_chat_assistant_audio",
        tracking_legacy_synthesize,
    )

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
    assert legacy_called["value"] is True


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
    assert (
        body["data"]["message"] == BusinessErrorCode.IMAGE_GENERATION_BLOCKED["message"]
    )
    assert (
        body["data"]["description"]
        == BusinessErrorCode.IMAGE_GENERATION_BLOCKED["message"]
    )
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
        assert isinstance(
            action, dict
        ), f"Each business_actions item must be a dict: {action}"
        assert (
            "action_type" in action and "message" in action
        ), f"Each business_actions item must have action_type and message: {action}"


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
        assert (
            "id" in msg
        ), f"Festival memory prompt message must have id, got message={msg}"
        assert isinstance(
            msg["id"], int
        ), f"Festival memory prompt message id must be int, got {type(msg['id']).__name__}"
        # 断言：投递后 memory.delivery_at 已更新
        db_session.refresh(memory)
        assert (
            memory.delivery_at is not None
        ), "memory.delivery_at should be set after delivery"
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
        assert (
            memory.delivery_at is None
        ), "When app version is too old, delivery must be skipped and delivery_at must remain null"
    finally:
        db_session.delete(memory)
        db_session.commit()
