"""Tests for WebSocket chat assistant TTS orchestration (split VoiceService APIs)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat_assistant_voice import synthesize_chat_assistant_audio
from app.services.voice_service import VoiceGenerationResult, VoiceService


@pytest.mark.asyncio
async def test_synthesize_uses_check_quota_before_generate_no_quota():
    voice_svc = MagicMock(spec=VoiceService)
    voice_svc.check_quota = AsyncMock(return_value=(True, 0, 10))
    voice_svc.prepare_synthesis_voice_id_and_text = MagicMock(
        return_value=("google/Zephyr", "hello")
    )
    voice_svc.resolve_generation_model = AsyncMock(
        return_value=("gemini-2.5-flash-tts", "subscription")
    )
    voice_svc.lookup_cached_voice = AsyncMock(return_value=None)
    voice_svc.generate_voice_no_quota_limit_check = AsyncMock(
        return_value=VoiceGenerationResult(
            gcs_url="gs://b/v.wav",
            gcs_http_url="https://storage.googleapis.com/b/v.wav",
            duration_seconds=1.0,
        )
    )
    voice_svc.record_voice_usage = AsyncMock()

    with patch(
        "app.services.chat_assistant_voice.is_gemini_voice",
        return_value=True,
    ), patch(
        "app.services.chat_assistant_voice.global_config_loaded_from_config_yaml"
    ) as mock_cfg:
        mock_cfg.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate = False

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

    voice_svc.check_quota.assert_awaited_once()
    voice_svc.generate_voice_no_quota_limit_check.assert_awaited_once()
    voice_svc.record_voice_usage.assert_awaited_once()
    assert audio_url == "https://storage.googleapis.com/b/v.wav"
    assert duration == 1.0


@pytest.mark.asyncio
async def test_synthesize_skips_tts_when_quota_denied():
    voice_svc = MagicMock(spec=VoiceService)
    voice_svc.check_quota = AsyncMock(return_value=(False, 2, 2))

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

    voice_svc.check_quota.assert_awaited_once()
    voice_svc.generate_voice_no_quota_limit_check.assert_not_called()
    assert audio_url is None
    assert duration is None
