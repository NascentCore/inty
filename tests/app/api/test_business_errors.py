from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints import agents as agents_v1
from app.api.v1.endpoints import chat as chat_v1
from app.api.v1.endpoints import chats as chats_v1
from app.api.v2.endpoints import chat as chat_v2
from app.core.agent import agent as agent_module
from app.models.user import AuthType
from app.schemas import User
from app.schemas.response import BusinessErrorCode
from app.services import agent_service, chat_history_service, chat_service
from app.services.global_services import subscription_service
from app.services.voice_service import VoiceService


def _make_user(
    user_id: str = "user-1",
    auth_type: AuthType = AuthType.GOOGLE,
    is_superuser: bool = False,
) -> User:
    return User(
        id=user_id,
        readable_id=f"readable-{user_id}",
        auth_type=auth_type.value if isinstance(auth_type, AuthType) else auth_type,
        is_active=True,
        is_superuser=is_superuser,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(agents_v1.router, prefix="/api/v1")
    app.include_router(chats_v1.router, prefix="/api/v1")
    app.include_router(chat_v1.router, prefix="/api/v1")
    app.include_router(chat_v2.router, prefix="/api/v2")

    async def override_db():
        yield None

    app.dependency_overrides[deps.get_async_db] = override_db

    yield app

    app.dependency_overrides.clear()


@contextlib.contextmanager
def _client_with_user(app: FastAPI, user: User):
    async def override_current_active_user() -> User:
        return user

    app.dependency_overrides[deps.get_current_active_user] = (
        override_current_active_user
    )

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(deps.get_current_active_user, None)


def test_create_agent_limit_returns_business_error(monkeypatch: pytest.MonkeyPatch, test_app: FastAPI):
    async def fake_check_agent_creation_limit(db, current_user):
        return False, 6, 6

    monkeypatch.setattr(
        subscription_service,
        "check_agent_creation_limit",
        fake_check_agent_creation_limit,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(test_app, user) as client:
        response = client.post(
            "/api/v1/ai/agents",
            json={"name": "Test Agent", "gender": "FEMALE", "visibility": "PUBLIC"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.AGENT_CREATION_LIMIT_REACHED["code"]
    assert body["message"] == BusinessErrorCode.AGENT_CREATION_LIMIT_REACHED["message"]
    assert body["data"]["error_code"] == BusinessErrorCode.AGENT_CREATION_LIMIT_REACHED["error_code"]
    assert body["data"]["used_count"] == 6
    assert body["data"]["limit"] == 6
    assert body["data"]["feature"] == "agent_creation"


def test_text_to_image_limit_returns_business_error(monkeypatch: pytest.MonkeyPatch, test_app: FastAPI):
    async def fake_check_image_gen_limit(db, current_user):
        return False, 3, 3

    monkeypatch.setattr(
        subscription_service,
        "check_image_gen_limit",
        fake_check_image_gen_limit,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(test_app, user) as client:
        response = client.post(
            "/api/v1/ai/agents/text-to-image",
            json={"prompt": "generate image", "count": 1},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.IMAGE_GENERATION_LIMIT_REACHED["code"]
    assert (
        body["message"]
        == BusinessErrorCode.IMAGE_GENERATION_LIMIT_REACHED["message"]
    )
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.IMAGE_GENERATION_LIMIT_REACHED["error_code"]
    )
    assert body["data"]["used_count"] == 3
    assert body["data"]["limit"] == 3
    assert body["data"]["feature"] == "background_generation"


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

    def fake_add_user_message(session_id, message):
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


def test_generate_message_voice_guest_login_required(
    monkeypatch: pytest.MonkeyPatch, test_app: FastAPI
):
    _stub_voice_generation_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GUEST)

    with _client_with_user(test_app, user) as client:
        response = client.post(
            "/api/v1/chats/agents/agent-1/messages/1/voice",
            params={"language": "zh"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.GUEST_LOGIN_REQUIRED["code"]
    assert body["data"]["error_code"] == BusinessErrorCode.GUEST_LOGIN_REQUIRED["error_code"]
    assert body["data"]["used_count"] == 2
    assert body["data"]["limit"] == 2


def test_generate_message_voice_limit_reached_for_signed_in_user(
    monkeypatch: pytest.MonkeyPatch, test_app: FastAPI
):
    _stub_voice_generation_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(test_app, user) as client:
        response = client.post(
            "/api/v1/chats/agents/agent-1/messages/1/voice",
            params={"language": "zh"},
        )

    body = response.json()

    assert response.status_code == 200
    assert (
        body["code"]
        == BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED["code"]
    )
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED["error_code"]
    )
    assert body["data"]["used_count"] == 2
    assert body["data"]["limit"] == 2


def test_update_chat_settings_requires_subscription(
    monkeypatch: pytest.MonkeyPatch, test_app: FastAPI
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

    with _client_with_user(test_app, user) as client:
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

    def fake_add_user_message(session_id, message):
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


def test_v1_chat_completions_guest_requires_login(
    monkeypatch: pytest.MonkeyPatch, test_app: FastAPI
):
    _stub_chat_completion_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GUEST)

    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "zh",
    }

    with _client_with_user(test_app, user) as client:
        response = client.post("/api/v1/chat/completions/agent-1", json=payload)

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.GUEST_LOGIN_REQUIRED["code"]
    assert body["data"]["error_code"] == BusinessErrorCode.GUEST_LOGIN_REQUIRED["error_code"]
    assert body["data"]["used_count"] == 5
    assert body["data"]["daily_limit"] == 5


def test_v1_chat_completions_subscription_required(
    monkeypatch: pytest.MonkeyPatch, test_app: FastAPI
):
    _stub_chat_completion_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "zh",
    }

    with _client_with_user(test_app, user) as client:
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


def test_v2_chat_completions_handles_business_error(
    monkeypatch: pytest.MonkeyPatch, test_app: FastAPI
):
    _stub_chat_completion_dependencies(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "model": "chatbot",
        "language": "zh",
    }

    with _client_with_user(test_app, user) as client:
        response = client.post("/api/v2/chat/completions/agent-1", json=payload)

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.SUBSCRIPTION_REQUIRED["code"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.SUBSCRIPTION_REQUIRED["error_code"]
    )
    assert body["data"]["used_count"] == 5
    assert body["data"]["daily_limit"] == 5


def _stub_generate_chat_image(monkeypatch: pytest.MonkeyPatch):
    async def fake_generate_chat_image(*args, **kwargs):
        raise HTTPException(
            status_code=499,
            detail={
                "error_info": BusinessErrorCode.SUBSCRIPTION_REQUIRED,
                "extra_data": {"used_count": 4, "limit": 4},
            },
        )

    monkeypatch.setattr(chat_service, "generate_chat_image", fake_generate_chat_image)


def test_v1_chat_generate_image_wraps_business_error(
    monkeypatch: pytest.MonkeyPatch, test_app: FastAPI
):
    _stub_generate_chat_image(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(test_app, user) as client:
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
    assert body["data"]["limit"] == 4


def test_v1_chats_generate_image_wraps_business_error(
    monkeypatch: pytest.MonkeyPatch, test_app: FastAPI
):
    _stub_generate_chat_image(monkeypatch)

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(test_app, user) as client:
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
    assert body["data"]["limit"] == 4
