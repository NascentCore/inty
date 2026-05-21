"""Tests for WebSocket voice_message TTS service (fake TTS + Postgres)."""

import uuid as uuid_module

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.core.voice.tts_api import VoiceMessageNarrationMode
from app.external_services.fakes.tts import FakeTextToSpeechAPI
from app.models.chat_history import ChatHistory
from app.services import chat_history_service
from app.services.chat_service import generate_session_id
from app.services.chat_ws_voice_message import (
    ChatWsVoiceMessageTtsInput,
    synthesize_chat_ws_voice_message,
)
from app.services.voice_service import VoiceService


@pytest.fixture
def sync_db_session():
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
async def async_db_session():
    _db = global_config_loaded_from_config_yaml.database
    engine = create_async_engine(
        str(_db.async_url),
        pool_size=1,
        max_overflow=0,
    )
    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def voice_service_with_fake_tts():
    assert global_config_loaded_from_config_yaml.tts.use_fake_tts is True
    service = VoiceService()
    assert isinstance(service.tts_api, FakeTextToSpeechAPI)
    service.config.enabled = True
    return service


@pytest.mark.asyncio
async def test_synthesize_chat_ws_voice_message_empty_transcript_returns_none(
    voice_service_with_fake_tts: VoiceService,
    async_db_session: AsyncSession,
):
    result = await synthesize_chat_ws_voice_message(
        ChatWsVoiceMessageTtsInput(transcript="   "),
        db=async_db_session,
        voice_svc=voice_service_with_fake_tts,
        voice_id="4tRn1lSkEn13EVTuqb0g",
        language="en",
        voice_message_narration_mode=VoiceMessageNarrationMode.DIALOGUE_ONLY,
    )
    assert result is None


@pytest.mark.asyncio
async def test_synthesize_chat_ws_voice_message_uses_fake_tts_without_user(
    voice_service_with_fake_tts: VoiceService,
    async_db_session: AsyncSession,
):
    result = await synthesize_chat_ws_voice_message(
        ChatWsVoiceMessageTtsInput(transcript="hello voice"),
        db=async_db_session,
        voice_svc=voice_service_with_fake_tts,
        voice_id="4tRn1lSkEn13EVTuqb0g",
        language="en",
        voice_message_narration_mode=VoiceMessageNarrationMode.DIALOGUE_ONLY,
    )
    assert result is not None
    if global_config_loaded_from_config_yaml.gcs.use_fake_gcs:
        assert result.gcs_http_url.startswith("file://")
    else:
        assert result.gcs_http_url.startswith("https://storage.googleapis.com/")
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_synthesize_chat_ws_voice_message_persists_audio_url_on_postgres(
    voice_service_with_fake_tts: VoiceService,
    async_db_session: AsyncSession,
    sync_db_session,
):
    chat_id = f"chat-ws-voice-svc-{uuid_module.uuid4().hex}"
    session_id = generate_session_id(chat_id)
    try:
        message_id = await chat_history_service.add_ai_message_sync_async(
            session_id,
            "assistant bubble",
            agent_id="agent-voice-svc-test",
            meta_data={"reply_modality": "voice_message"},
        )
        assert message_id is not None

        voice_result = await synthesize_chat_ws_voice_message(
            ChatWsVoiceMessageTtsInput(transcript="spoken line"),
            db=async_db_session,
            voice_svc=voice_service_with_fake_tts,
            voice_id="4tRn1lSkEn13EVTuqb0g",
            language="en",
            voice_message_narration_mode=VoiceMessageNarrationMode.DIALOGUE_ONLY,
        )
        assert voice_result is not None

        updated = await chat_history_service.update_message_audio_url(
            async_db_session,
            session_id,
            str(message_id),
            voice_result.gcs_http_url,
            voice_result.duration_seconds,
        )
        assert updated is True

        row = (
            sync_db_session.query(ChatHistory)
            .filter(ChatHistory.id == message_id)
            .one()
        )
        assert row.audio_url == voice_result.gcs_http_url
    finally:
        sync_db_session.execute(
            delete(ChatHistory).where(
                ChatHistory.session_id == uuid_module.UUID(session_id)
            )
        )
        sync_db_session.commit()
