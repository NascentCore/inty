"""Business error and integration tests for chats endpoints."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from sqlalchemy.exc import MissingGreenlet

from app.api import deps
from app.api.v1.endpoints import chats as chats_v1
from app.core.voice.tts_api import VoiceMessageNarrationMode
from app.models.user import AuthType
from app.schemas.response import BusinessErrorCode
from app.services import agent_service, chat_history_service, chat_service
from app.services.global_services import (
    subscription_service as global_subscription_service,
)
from app.services.voice_service import VoiceGenerationResult
from app.services.voice_service import voice_service as global_voice_service
from tests.app.api.v1.endpoints.conftest import (
    _client_with_user,
    _create_mock_db_session,
    _make_user,
)


class _ExpiringUser:
    """模拟 rollback 后 ORM 用户对象属性失效（访问 id 抛 MissingGreenlet）。"""

    def __init__(self, user_id: str, *, is_superuser: bool = False):
        self._user_id = user_id
        self._expired = False
        self.is_superuser = is_superuser

    @property
    def id(self) -> str:
        if self._expired:
            raise MissingGreenlet("greenlet_spawn has not been called")
        return self._user_id

    def expire(self) -> None:
        self._expired = True


@pytest.fixture
def chats_business_error_app() -> FastAPI:
    app = FastAPI()
    app.include_router(chats_v1.router, prefix="/api/v1")

    async def override_db():
        mock_db = _create_mock_db_session()
        yield mock_db

    app.dependency_overrides[deps.get_async_db] = override_db
    app.dependency_overrides[deps.get_subscription_service] = (
        lambda: global_subscription_service
    )
    app.dependency_overrides[deps.get_voice_service] = (
        lambda: global_voice_service
    )

    yield app

    app.dependency_overrides.clear()


def _stub_voice_generation_dependencies(monkeypatch: pytest.MonkeyPatch):
    from app.services import chat_assistant_voice

    async def fake_get_agent_for_chat(db, agent_id):
        return {"voice_id": "voice-1", "gender": "FEMALE"}

    async def fake_get_chat_by_user_and_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_message_content(db, session_id, message_id):
        return "hello"

    async def fake_produce_voice_for_user(*args, **kwargs):
        return None, False, 2, 2

    def fake_add_user_message(session_id, message, meta_data=None):
        return None

    monkeypatch.setattr(
        agent_service, "get_agent_for_chat", fake_get_agent_for_chat
    )
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
        chat_assistant_voice,
        "produce_voice_for_user",
        fake_produce_voice_for_user,
    )
    monkeypatch.setattr(
        chat_history_service,
        "add_user_message",
        fake_add_user_message,
    )


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
    assert (
        body["code"] == BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED["code"]
    )
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED["error_code"]
    )
    assert body["data"]["used_count"] == 2
    assert body["data"]["limit"] == 2


def test_generate_message_voice_success_includes_gcs_urls(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    captured = {}

    async def fake_get_agent_for_chat(db, agent_id):
        return {"voice_id": "google/Zephyr", "gender": "FEMALE", "settings": {}}

    async def fake_get_chat_by_user_and_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_message_content(db, session_id, message_id):
        return "hello"

    async def fake_produce_voice_for_user(*args, **kwargs):
        captured["voice_message_narration_mode"] = kwargs.get(
            "voice_message_narration_mode"
        )
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

    async def fake_update_message_audio_url(
        db, session_id, message_id, audio_url, audio_duration
    ):
        return True

    monkeypatch.setattr(
        agent_service, "get_agent_for_chat", fake_get_agent_for_chat
    )
    monkeypatch.setattr(
        chat_service,
        "get_chat_by_user_and_agent",
        fake_get_chat_by_user_and_agent,
    )
    from app.services import chat_assistant_voice

    monkeypatch.setattr(
        chat_history_service,
        "get_message_content",
        fake_get_message_content,
    )
    monkeypatch.setattr(
        chat_assistant_voice,
        "produce_voice_for_user",
        fake_produce_voice_for_user,
    )
    monkeypatch.setattr(
        chat_history_service,
        "update_message_audio_url",
        fake_update_message_audio_url,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chats_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chats/agents/agent-1/messages/1/voice",
            params={"language": "en"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 200
    assert (
        body["data"]["gcs_url"]
        == "gs://test-bucket/voice/202603/voice_test.wav"
    )
    assert (
        body["data"]["gcs_http_url"]
        == "https://storage.googleapis.com/test-bucket/voice/202603/voice_test.wav"
    )
    assert (
        body["data"]["audio_url"]
        == "https://storage.googleapis.com/test-bucket/voice/202603/voice_test.wav"
    )
    assert body["data"]["audio_duration"] == 1.23
    assert (
        captured["voice_message_narration_mode"]
        == VoiceMessageNarrationMode.DIALOGUE_ONLY
    )


def test_generate_message_voice_prefers_chat_settings_voice_id(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    captured = {}

    async def fake_get_agent_for_chat(db, agent_id):
        return {
            "voice_id": "google/Puck",
            "gender": "FEMALE",
            "settings": {
                "voice_message_narration_mode": "dialogue_and_stage_directions"
            },
        }

    async def fake_get_chat_by_user_and_agent(db, user_id, agent_id):
        return SimpleNamespace(
            id="chat-1",
            agent_id=agent_id,
            settings=SimpleNamespace(voice_id="google/Zephyr"),
        )

    async def fake_get_message_content(db, session_id, message_id):
        return "hello"

    async def fake_produce_voice_for_user(*args, **kwargs):
        captured["voice_id"] = kwargs.get("voice_id")
        captured["voice_message_narration_mode"] = kwargs.get(
            "voice_message_narration_mode"
        )
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

    async def fake_update_message_audio_url(
        db, session_id, message_id, audio_url, audio_duration
    ):
        return True

    from app.services import chat_assistant_voice

    monkeypatch.setattr(
        agent_service, "get_agent_for_chat", fake_get_agent_for_chat
    )
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
        chat_assistant_voice,
        "produce_voice_for_user",
        fake_produce_voice_for_user,
    )
    monkeypatch.setattr(
        chat_history_service,
        "update_message_audio_url",
        fake_update_message_audio_url,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chats_business_error_app, user) as client:
        response = client.post(
            "/api/v1/chats/agents/agent-1/messages/1/voice",
            params={"language": "en"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 200
    assert captured["voice_id"] == "google/Zephyr"
    assert (
        captured["voice_message_narration_mode"]
        == VoiceMessageNarrationMode.DIALOGUE_AND_STAGE_DIRECTIONS
    )
    assert body["data"]["voice_id"] == "google/Zephyr"


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
        global_subscription_service,
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


def test_update_chat_settings_rejects_non_gemini_voice_id(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    async def fake_get_agent(db, agent_id):
        return SimpleNamespace(id=agent_id)

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            id="settings-1", voice_enabled=False, voice_id=None
        )

    async def fake_get_subscription_status(db, user_id):
        return SimpleNamespace(is_subscribed=True)

    async def fake_update_chat_settings(db, chat_id, settings_update):
        return SimpleNamespace(id="settings-1")

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
        global_subscription_service,
        "get_user_subscription_status",
        fake_get_subscription_status,
    )
    monkeypatch.setattr(
        chat_service,
        "update_chat_settings",
        fake_update_chat_settings,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(chats_business_error_app, user) as client:
        response = client.put(
            "/api/v1/chats/agents/agent-1/settings",
            json={"voice_id": "11labs/EXAVITQu4vr4xnSDxMaL"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only Gemini voices are supported in chat settings for now."
    )


def test_update_chat_settings_accepts_default_voice_sentinel_and_clears_voice_id(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    captured_voice_id = "not-called"

    async def fake_get_agent(db, agent_id):
        return SimpleNamespace(id=agent_id)

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            id="settings-1", chat_id=chat_id, voice_id="google/Puck"
        )

    async def fake_get_subscription_status(db, user_id):
        return SimpleNamespace(is_subscribed=True)

    async def fake_update_chat_settings(db, chat_id, settings_update):
        nonlocal captured_voice_id
        captured_voice_id = settings_update.voice_id
        return SimpleNamespace(
            id="settings-1",
            user_id="user-1",
            agent_id="agent-1",
            chat_id=chat_id,
            chat_mode=None,
            language="en",
            voice_enabled=True,
            voice_id=settings_update.voice_id,
            style_prompt=None,
            premium_mode=False,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

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
        global_subscription_service,
        "get_user_subscription_status",
        fake_get_subscription_status,
    )
    monkeypatch.setattr(
        chat_service, "update_chat_settings", fake_update_chat_settings
    )

    user = _make_user(auth_type=AuthType.GOOGLE)
    with _client_with_user(chats_business_error_app, user) as client:
        response = client.put(
            "/api/v1/chats/agents/agent-1/settings",
            json={"voice_id": " default "},
        )

    assert response.status_code == 200
    assert captured_voice_id is None
    assert response.json()["data"]["voice_id"] is None


def test_get_agent_chat_messages_recovers_when_festival_delivery_hits_missing_greenlet(
    monkeypatch: pytest.MonkeyPatch,
):
    app = FastAPI()
    app.include_router(chats_v1.router, prefix="/api/v1")

    mock_db = _create_mock_db_session()
    rollback_called = False

    async def _rollback():
        nonlocal rollback_called
        rollback_called = True

    mock_db.rollback = AsyncMock(side_effect=_rollback)

    async def override_db():
        yield mock_db

    app.dependency_overrides[deps.get_async_db] = override_db

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_deliver_festival(*args, **kwargs):
        raise MissingGreenlet("greenlet_spawn has not been called")

    async def fake_get_unlocked_surprise_snap_message_ids(db, user_id):
        if not rollback_called:
            raise MissingGreenlet(
                "session should be rolled back before continuing"
            )
        return set()

    def fake_get_messages_paginated(*args, **kwargs):
        return {
            "messages": [{"id": 1, "role": "assistant", "content": "ok"}],
            "total": 1,
        }

    monkeypatch.setattr(
        chats_v1.chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(chats_v1, "is_festival_memory_enabled", lambda _: True)
    monkeypatch.setattr(
        chats_v1,
        "deliver_festival_memories_for_user_agent",
        fake_deliver_festival,
    )
    monkeypatch.setattr(
        chats_v1,
        "get_unlocked_surprise_snap_message_ids",
        fake_get_unlocked_surprise_snap_message_ids,
    )
    monkeypatch.setattr(
        chats_v1.chat_history_service,
        "get_messages_paginated",
        fake_get_messages_paginated,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)
    with _client_with_user(app, user) as client:
        response = client.get(
            "/api/v1/chats/agents/agent-1/messages",
            params={"limit": 20, "offset": 0, "order": "desc"},
            headers={"appVersionCode": "9999"},
        )

    body = response.json()
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert rollback_called is True
    assert body["total"] == 1
    assert body["messages"][0]["content"] == "ok"


def test_get_agent_chat_messages_uses_cached_user_id_after_chat_creation_rollback(
    monkeypatch: pytest.MonkeyPatch,
):
    app = FastAPI()
    app.include_router(chats_v1.router, prefix="/api/v1")

    mock_db = _create_mock_db_session()

    async def override_db():
        yield mock_db

    app.dependency_overrides[deps.get_async_db] = override_db

    user = _ExpiringUser("user-expire-1")

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        assert user_id == "user-expire-1"
        # 模拟 service 内 rollback 后，ORM 用户对象属性失效
        user.expire()
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_unlocked_surprise_snap_message_ids(db, user_id):
        assert user_id == "user-expire-1"
        return set()

    def fake_get_messages_paginated(*args, **kwargs):
        assert kwargs["user_id"] == "user-expire-1"
        return {
            "messages": [{"id": 1, "role": "assistant", "content": "ok"}],
            "total": 1,
        }

    monkeypatch.setattr(
        chats_v1.chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(chats_v1, "is_festival_memory_enabled", lambda _: False)
    monkeypatch.setattr(
        chats_v1,
        "get_unlocked_surprise_snap_message_ids",
        fake_get_unlocked_surprise_snap_message_ids,
    )
    monkeypatch.setattr(
        chats_v1.chat_history_service,
        "get_messages_paginated",
        fake_get_messages_paginated,
    )

    with _client_with_user(app, user) as client:
        response = client.get(
            "/api/v1/chats/agents/agent-1/messages",
            params={"limit": 20, "offset": 0, "order": "desc"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_agent_chat_settings_uses_cached_user_id_after_chat_creation_rollback(
    monkeypatch: pytest.MonkeyPatch,
):
    app = FastAPI()
    app.include_router(chats_v1.router, prefix="/api/v1")

    mock_db = _create_mock_db_session()

    async def override_db():
        yield mock_db

    app.dependency_overrides[deps.get_async_db] = override_db

    user = _ExpiringUser("user-expire-2")

    async def fake_get_agent(db, agent_id):
        return SimpleNamespace(id=agent_id)

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        assert user_id == "user-expire-2"
        user.expire()
        return SimpleNamespace(id="chat-2", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        assert user_id == "user-expire-2"
        return SimpleNamespace(
            id="settings-2",
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            language="en",
            voice_enabled=True,
            style_prompt=None,
            premium_mode=False,
            chat_mode=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

    monkeypatch.setattr(agent_service, "get_agent", fake_get_agent)
    monkeypatch.setattr(
        chats_v1.chat_service,
        "get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(
        chats_v1.chat_service,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )

    with _client_with_user(app, user) as client:
        response = client.get("/api/v1/chats/agents/agent-2/settings")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "settings-2"


def test_list_chat_modes_returns_three_modes(chats_business_error_app: FastAPI):
    """GET /chats/modes without agent_id returns the three user-facing chat modes."""
    user = _make_user(auth_type=AuthType.GOOGLE)
    with _client_with_user(chats_business_error_app, user) as client:
        response = client.get("/api/v1/chats/modes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    ids = [m["id"] for m in data]
    assert "flirting_mode_20250902" in ids
    assert "rp_mode_1225" in ids
    assert "immersive_mode_0309" in ids
    for m in data:
        assert "short_name" in m
        assert "name" in m
        assert "description" in m


def test_get_agent_chat_settings_returns_chat_mode_when_agent_default_in_three(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    """When agent mode_prompt is in USER_FACING_CHAT_MODE_IDS, GET settings returns chat_mode and available_chat_modes."""
    from app.core.agent.prompts import USER_FACING_CHAT_MODE_IDS

    async def fake_get_agent(db, agent_id):
        return SimpleNamespace(
            id=agent_id, mode_prompt=USER_FACING_CHAT_MODE_IDS[0]
        )

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            id="settings-1",
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            language="en",
            voice_enabled=True,
            style_prompt=None,
            premium_mode=False,
            chat_mode=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

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

    user = _make_user(auth_type=AuthType.GOOGLE)
    with _client_with_user(chats_business_error_app, user) as client:
        response = client.get("/api/v1/chats/agents/agent-1/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["chat_mode"] == USER_FACING_CHAT_MODE_IDS[0]
    assert "available_chat_modes" not in body


def test_get_agent_chat_settings_returns_null_chat_mode_when_agent_default_not_in_three(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    """When agent mode_prompt is not in USER_FACING_CHAT_MODE_IDS, GET settings returns chat_mode=null, available_chat_modes=null."""

    async def fake_get_agent(db, agent_id):
        return SimpleNamespace(id=agent_id, mode_prompt="purity_mode_0725")

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            id="settings-1",
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            language="en",
            voice_enabled=True,
            style_prompt=None,
            premium_mode=False,
            chat_mode=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

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

    user = _make_user(auth_type=AuthType.GOOGLE)
    with _client_with_user(chats_business_error_app, user) as client:
        response = client.get("/api/v1/chats/agents/agent-1/settings")
    assert response.status_code == 200
    body = response.json()
    assert body.get("chat_mode") is None
    assert "available_chat_modes" not in body


def test_update_chat_settings_accepts_valid_chat_mode(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    """PUT settings with chat_mode in USER_FACING_CHAT_MODE_IDS succeeds."""
    from app.core.agent.prompts import USER_FACING_CHAT_MODE_IDS

    async def fake_get_agent(db, agent_id):
        return SimpleNamespace(id=agent_id)

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(
            id="settings-1",
            chat_id=chat_id,
            chat_mode=None,
        )

    async def fake_get_subscription_status(db, user_id):
        return SimpleNamespace(is_subscribed=True)

    async def fake_update_chat_settings(db, chat_id, settings_update):
        return SimpleNamespace(
            id="settings-1",
            user_id="user-1",
            agent_id="agent-1",
            chat_id=chat_id,
            chat_mode=settings_update.chat_mode,
            language="en",
            voice_enabled=True,
            style_prompt=None,
            premium_mode=False,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

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
        global_subscription_service,
        "get_user_subscription_status",
        fake_get_subscription_status,
    )
    monkeypatch.setattr(
        chat_service, "update_chat_settings", fake_update_chat_settings
    )

    user = _make_user(auth_type=AuthType.GOOGLE)
    with _client_with_user(chats_business_error_app, user) as client:
        response = client.put(
            "/api/v1/chats/agents/agent-1/settings",
            json={"chat_mode": USER_FACING_CHAT_MODE_IDS[0]},
        )
    assert response.status_code == 200


def test_update_chat_settings_rejects_invalid_chat_mode(
    monkeypatch: pytest.MonkeyPatch, chats_business_error_app: FastAPI
):
    """PUT settings with chat_mode not in USER_FACING_CHAT_MODE_IDS returns 400."""

    async def fake_get_agent(db, agent_id):
        return SimpleNamespace(id=agent_id)

    async def fake_get_or_create_chat_by_agent(db, user_id, agent_id):
        return SimpleNamespace(id="chat-1", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(id="settings-1", chat_id=chat_id)

    async def fake_get_subscription_status(db, user_id):
        return SimpleNamespace(is_subscribed=True)

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
        global_subscription_service,
        "get_user_subscription_status",
        fake_get_subscription_status,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)
    with _client_with_user(chats_business_error_app, user) as client:
        response = client.put(
            "/api/v1/chats/agents/agent-1/settings",
            json={"chat_mode": "invalid_mode_id"},
        )
    assert response.status_code == 400
