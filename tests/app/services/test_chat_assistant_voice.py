"""Tests for WebSocket chat assistant TTS orchestration (split VoiceService APIs)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat_assistant_voice import (
    produce_voice_for_user,
    synthesize_chat_assistant_audio,
)
from app.services.voice_service import VoiceGenerationResult, VoiceService


@pytest.mark.asyncio
async def test_produce_voice_for_user_denied_returns_quota_tuple():
    voice_svc = MagicMock(spec=VoiceService)

    with patch(
        "app.services.chat_assistant_voice.subscription_service.check_voice_generation_limit",
        new_callable=AsyncMock,
        return_value=(False, 2, 2),
    ):
        result, is_allowed, used_count, limit = await produce_voice_for_user(
            voice_svc=voice_svc,
            db=MagicMock(),
            user=MagicMock(id="u1"),
            text="hello",
            voice_id="google/Zephyr",
            language="en",
            agent_gender="FEMALE",
            voice_message_narration_mode=None,
        )

    assert result is None
    assert is_allowed is False
    assert used_count == 2
    assert limit == 2
    voice_svc.generate_voice_no_quota_limit_check.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_uses_produce_voice_for_user():
    voice_svc = MagicMock(spec=VoiceService)
    expected = (
        VoiceGenerationResult(
            gcs_url="gs://b/v.wav",
            gcs_http_url="https://storage.googleapis.com/b/v.wav",
            duration_seconds=1.0,
        ),
        True,
        0,
        10,
    )

    with patch(
        "app.services.chat_assistant_voice.produce_voice_for_user",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_produce:
        audio_url, duration = await synthesize_chat_assistant_audio(
            db=MagicMock(),
            session_id="sess-1",
            ai_message_id=None,
            voice_enabled=True,
            chat_voice_id="google/Zephyr",
            agent_voice_id=None,
            agent_gender="FEMALE",
            agent_settings={},
            language="en",
            current_user=MagicMock(id="u1"),
            voice_svc=voice_svc,
            response_text_content="hello",
            use_companion=False,
            companion_reply_modality="",
            companion_voice_script="",
        )

    mock_produce.assert_awaited_once()
    assert audio_url == "https://storage.googleapis.com/b/v.wav"
    assert duration == 1.0


@pytest.mark.asyncio
async def test_synthesize_skips_tts_when_quota_denied():
    voice_svc = MagicMock(spec=VoiceService)

    with patch(
        "app.services.chat_assistant_voice.produce_voice_for_user",
        new_callable=AsyncMock,
        return_value=(None, False, 2, 2),
    ):
        audio_url, duration = await synthesize_chat_assistant_audio(
            db=MagicMock(),
            session_id="sess-1",
            ai_message_id=None,
            voice_enabled=True,
            chat_voice_id="google/Zephyr",
            agent_voice_id=None,
            agent_gender="FEMALE",
            agent_settings={},
            language="en",
            current_user=MagicMock(id="u1"),
            voice_svc=voice_svc,
            response_text_content="hello",
            use_companion=False,
            companion_reply_modality="",
            companion_voice_script="",
        )

    assert audio_url is None
    assert duration is None


@pytest.mark.asyncio
async def test_synthesize_skips_companion_voice_message_modality():
    voice_svc = MagicMock(spec=VoiceService)

    with patch(
        "app.services.chat_assistant_voice.produce_voice_for_user",
        new_callable=AsyncMock,
    ) as mock_produce:
        audio_url, duration = await synthesize_chat_assistant_audio(
            db=MagicMock(),
            session_id="sess-1",
            ai_message_id=None,
            voice_enabled=True,
            chat_voice_id="google/Zephyr",
            agent_voice_id=None,
            agent_gender="FEMALE",
            agent_settings={},
            language="en",
            current_user=MagicMock(id="u1"),
            voice_svc=voice_svc,
            response_text_content="hello",
            use_companion=True,
            companion_reply_modality="voice_message",
            companion_voice_script="spoken",
        )

    mock_produce.assert_not_called()
    assert audio_url is None
    assert duration is None
