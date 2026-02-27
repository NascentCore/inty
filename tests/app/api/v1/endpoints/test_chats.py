"""Business error and integration tests for chats endpoints."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from app.api import deps
from app.api.v1.endpoints import chats as chats_v1
from app.models.user import AuthType
from app.schemas.response import BusinessErrorCode, UsageLimitExceeded
from app.services import agent_service, chat_history_service, chat_service
from app.services.global_services import subscription_service
from app.services.voice_service import VoiceService
from tests.app.api.v1.endpoints.conftest import (
    _client_with_user,
    _create_mock_db_session,
    _make_user,
)


@pytest.fixture
def chats_business_error_app() -> FastAPI:
    app = FastAPI()
    app.include_router(chats_v1.router, prefix="/api/v1")

    async def override_db():
        mock_db = _create_mock_db_session()
        yield mock_db

    app.dependency_overrides[deps.get_async_db] = override_db

    yield app

    app.dependency_overrides.clear()


def _stub_voice_generation_dependencies(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_agent_for_chat(db, agent_id):
        return {"voice_id": "voice-1", "gender": "FEMALE"}

    async def fake_get_chat_by_user_and_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_message_content(db, session_id, message_id):
        return "hello"

    async def fake_generate_voice(self, *args, **kwargs):  # pragma: no cover - stub
        return None

    async def fake_check_voice_limit(db, user):
        return False, 2, 2

    def fake_add_user_message(session_id, message, meta_data=None):
        return None

    monkeypatch.setattr(agent_service, "get_agent_for_chat", fake_get_agent_for_chat)
    monkeypatch.setattr(
        chat_service,
        "get_chat_by_user_and_agent",
        fake_get_chat_by_user_and_agent,
    )
    monkeypatch.setattr(
        chat_history_service,
        "get_message_content",
        fake_get_message_content,
    )
    monkeypatch.setattr(
        VoiceService,
        "generate_voice",
        fake_generate_voice,
    )
    monkeypatch.setattr(
        subscription_service,
        "check_voice_generation_limit",
        fake_check_voice_limit,
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


def test_generate_message_voice_guest_login_required(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    _stub_voice_generation_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GUEST)

    with _client_with_user(chats_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chats/agents/agent-1/messages/1/voice",
            params={"language": "zh"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.GUEST_LOGIN_REQUIRED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.GUEST_LOGIN_REQUIRED["error_code"]
    )
    assert body["data"]["used_count"] == 2
    assert body["data"]["limit"] == 2


def test_generate_message_voice_limit_reached_for_signed_in_user(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    _stub_voice_generation_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chats_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chats/agents/agent-1/messages/1/voice",
            params={"language": "zh"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED["error_code"]
    )
    assert body["data"]["used_count"] == 2
    assert body["data"]["limit"] == 2


def test_update_chat_settings_requires_subscription(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    async def fake_get_agent(db, agent_id):
        return SimpleNamespace(id=agent_id)

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(id="settings-1", voice_enabled=False)

    async def fake_get_subscription_status(db, user_id):
        return SimpleNamespace(is_subscribed=False)

    monkeypatch.setattr(agent_service, "get_agent", fake_get_agent)
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
    monkeypatch.setattr(
        subscription_service,
        "get_user_subscription_status",
        fake_get_subscription_status,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chats_business_error_app, user) as client:
        response = client.put(
            "/api/v1/chats/agents/agent-1/settings",
            json={"style_prompt": "custom style"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.SUBSCRIPTION_REQUIRED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.SUBSCRIPTION_REQUIRED["error_code"]
    )
    assert body["data"].get("used_count") is None


def test_v1_chats_generate_image_wraps_business_error(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    _stub_generate_chat_image(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chats_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chats/agents/agent-1/generate-image",
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
