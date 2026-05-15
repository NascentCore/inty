"""Unit tests for ``synthesize_voice_for_persisted_chat_message`` (REST + companion tool shared path)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.user import AuthType
from app.services import chat_message_voice_synthesis as synth_mod
from app.services.voice_service import VoiceGenerationResult


@pytest.mark.asyncio
async def test_synthesize_success_persists_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    db = AsyncMock()
    user = SimpleNamespace(id="u1", auth_type=AuthType.EMAIL)

    async def fake_get_agent_for_chat(db_inner, agent_id):
        assert agent_id == "ag1"
        return {"voice_id": "v-agent", "gender": "FEMALE", "settings": {}}

    async def fake_get_chat_by_user_and_agent(*, db, user_id, agent_id):
        return SimpleNamespace(
            id="chat-db-1",
            agent_id=agent_id,
            settings=SimpleNamespace(voice_id=None),
        )

    async def fake_get_message_content(*, db, session_id, message_id):
        return "speak me"

    updates: list[tuple] = []

    async def fake_update_message_audio_url(**kwargs):
        updates.append(
            (
                kwargs.get("session_id"),
                kwargs.get("message_id"),
                kwargs.get("audio_url"),
            )
        )
        return True

    async def fake_generate_voice(**kwargs):
        return VoiceGenerationResult(
            gcs_url="gs://b/o.mp3",
            gcs_http_url="https://storage.example/o.mp3",
            duration_seconds=1.23,
        )

    monkeypatch.setattr(
        synth_mod.agent_service, "get_agent_for_chat", fake_get_agent_for_chat
    )
    monkeypatch.setattr(
        synth_mod.chat_service,
        "get_chat_by_user_and_agent",
        fake_get_chat_by_user_and_agent,
    )
    monkeypatch.setattr(
        synth_mod.chat_history_service,
        "get_message_content",
        fake_get_message_content,
    )
    monkeypatch.setattr(
        synth_mod.chat_history_service,
        "update_message_audio_url",
        fake_update_message_audio_url,
    )

    voice_svc = AsyncMock()
    voice_svc.generate_voice = fake_generate_voice
    sub_svc = AsyncMock()
    sub_svc.check_voice_generation_limit = AsyncMock(return_value=(True, 0, 99))

    res = await synth_mod.synthesize_voice_for_persisted_chat_message(
        db=db,
        current_user=user,
        agent_id="ag1",
        message_id="42",
        language="en",
        voice_svc=voice_svc,
        subscription_svc=sub_svc,
        expected_chat_id=None,
    )
    assert res.outcome == "success"
    assert res.audio_url == "https://storage.example/o.mp3"
    assert res.message_id == "42"
    assert updates and updates[0][1] == "42"


@pytest.mark.asyncio
async def test_chat_id_mismatch_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    db = AsyncMock()
    user = SimpleNamespace(id="u1", auth_type=AuthType.EMAIL)

    async def fake_get_agent_for_chat(db_inner, agent_id):
        return {"voice_id": "v", "gender": "FEMALE", "settings": {}}

    async def fake_get_chat_by_user_and_agent(*, db, user_id, agent_id):
        return SimpleNamespace(id="real-chat", settings=None)

    called: list[str] = []

    async def fake_get_message_content(*, db, session_id, message_id):
        called.append("content")
        return "x"

    monkeypatch.setattr(
        synth_mod.agent_service, "get_agent_for_chat", fake_get_agent_for_chat
    )
    monkeypatch.setattr(
        synth_mod.chat_service,
        "get_chat_by_user_and_agent",
        fake_get_chat_by_user_and_agent,
    )
    monkeypatch.setattr(
        synth_mod.chat_history_service,
        "get_message_content",
        fake_get_message_content,
    )

    voice_svc = AsyncMock()
    sub_svc = AsyncMock()

    res = await synth_mod.synthesize_voice_for_persisted_chat_message(
        db=db,
        current_user=user,
        agent_id="ag1",
        message_id="1",
        language="zh",
        voice_svc=voice_svc,
        subscription_svc=sub_svc,
        expected_chat_id="wrong-chat-id",
    )
    assert res.outcome == "chat_id_mismatch"
    assert not called
