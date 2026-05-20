"""Tests for split VoiceService APIs (model resolve, cache, no-quota generate)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.voice.tts_api import TTS_PROVIDER_GEMINI
from app.services.voice_cache_service import voice_cache_service
from app.services.voice_service import VoiceGenerationResult, VoiceService


@pytest.fixture
def voice_service() -> VoiceService:
    service = VoiceService()
    service.config.enabled = True
    return service


@pytest.mark.asyncio
async def test_resolve_tts_model_gemini_without_user_uses_config(
    voice_service: VoiceService,
):
    from app.core.config import global_config_loaded_from_config_yaml

    model, source = await voice_service.resolve_tts_model(
        provider_selected=TTS_PROVIDER_GEMINI,
        db=None,
        user=None,
    )
    assert model == global_config_loaded_from_config_yaml.agent.free_user_chat_tts_model
    assert source == "config"


@pytest.mark.asyncio
async def test_voice_cache_get_cached_voice_returns_voice_generation_result():
    with patch.object(
        voice_cache_service.gcs_service,
        "check_voice_file_exists",
        return_value=True,
    ), patch(
        "app.services.voice_cache_service.VoiceCacheService._update_cache_hit_async",
        new_callable=AsyncMock,
    ):
        db = MagicMock()
        db.execute = AsyncMock(
            return_value=MagicMock(
                one_or_none=MagicMock(
                    return_value=MagicMock(
                        audio_url="https://storage.googleapis.com/test-bucket/voice/cached.wav",
                        duration=1.5,
                    )
                )
            )
        )
        result = await voice_cache_service.get_cached_voice(
            db,
            "hello",
            "google/Zephyr",
            "gemini-2.5-flash-tts",
            "en",
        )

    assert isinstance(result, VoiceGenerationResult)
    assert result.gcs_url == "gs://test-bucket/voice/cached.wav"
    assert result.duration_seconds == 1.5


@pytest.mark.asyncio
async def test_record_voice_usage_calls_subscription(voice_service: VoiceService):
    user = MagicMock()
    user.id = "user-1"
    db = MagicMock()

    with patch(
        "app.services.voice_service.subscription_service.record_usage",
        new_callable=AsyncMock,
    ) as mock_record:
        await voice_service.record_voice_usage(
            db=db,
            user=user,
            text_length=5,
            voice_id="google/Zephyr",
            cached=True,
        )

    mock_record.assert_awaited_once()
    assert mock_record.await_args.args[2] == "voice_generation"


@pytest.mark.asyncio
@patch.object(VoiceService, "_call_tts_api", new_callable=AsyncMock)
@patch(
    "app.services.voice_service.GCSService.upload_voice_file", new_callable=AsyncMock
)
async def test_generate_voice_no_quota_limit_check_succeeds(
    mock_upload: AsyncMock,
    mock_tts: AsyncMock,
    voice_service: VoiceService,
):
    mock_tts.return_value = (b"wav", 1.0, "audio/wav", TTS_PROVIDER_GEMINI)
    mock_upload.return_value = (
        "https://storage.googleapis.com/test-bucket/voice/out.wav"
    )

    result = await voice_service.generate_voice_no_quota_limit_check(
        text="hello",
        voice_id="google/Zephyr",
        language="en",
        model="gemini-2.5-flash-tts",
        model_source="config",
        agent_gender=None,
        voice_message_narration_mode=None,
        gemini_source_model=None,
    )

    assert isinstance(result, VoiceGenerationResult)
    mock_tts.assert_awaited_once()
