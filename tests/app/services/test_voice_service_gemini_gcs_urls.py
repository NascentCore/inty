"""Tests for Gemini TTS voice result GCS URL fields."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.voice.tts_api import TTS_PROVIDER_ELEVENLABS, TTS_PROVIDER_GEMINI
from app.services.voice_service import (
    VoiceGenerationResult,
    VoiceService,
    build_voice_gcs_urls,
)


@pytest.fixture
def voice_service() -> VoiceService:
    service = VoiceService()
    service.config.enabled = True
    return service


def test_build_gcs_urls_accepts_gs_url():
    gcs_url, gcs_http_url = build_voice_gcs_urls("gs://test-bucket/voice/x.wav")
    assert gcs_url == "gs://test-bucket/voice/x.wav"
    assert gcs_http_url == "https://storage.googleapis.com/test-bucket/voice/x.wav"


@pytest.mark.asyncio
@patch.object(VoiceService, "_call_tts_api", new_callable=AsyncMock)
@patch(
    "app.services.voice_service.GCSService.upload_voice_file", new_callable=AsyncMock
)
async def test_generate_voice_returns_both_gcs_urls_for_gemini(
    mock_upload_voice_file: AsyncMock,
    mock_call_tts_api: AsyncMock,
    voice_service: VoiceService,
):
    mock_call_tts_api.return_value = (
        b"wav-bytes",
        1.25,
        "audio/wav",
        TTS_PROVIDER_GEMINI,
    )
    mock_upload_voice_file.return_value = (
        "https://storage.googleapis.com/test-bucket/voice/202603/voice_test.wav"
    )

    result = await voice_service.generate_voice(
        text="hello there",
        voice_id="google/Zephyr",
        language="en",
        model="gemini-2.5-flash-tts",
    )

    assert isinstance(result, VoiceGenerationResult)
    assert result.gcs_url == "gs://test-bucket/voice/202603/voice_test.wav"
    assert (
        result.gcs_http_url
        == "https://storage.googleapis.com/test-bucket/voice/202603/voice_test.wav"
    )
    assert result.duration_seconds == 1.25

    # Backward compatibility: existing callers can still unpack into (audio_url, duration).
    legacy_audio_url, legacy_duration = result
    assert legacy_audio_url == result.gcs_http_url
    assert legacy_duration == result.duration_seconds


@pytest.mark.asyncio
@patch.object(VoiceService, "_call_tts_api", new_callable=AsyncMock)
@patch(
    "app.services.voice_service.GCSService.upload_voice_file", new_callable=AsyncMock
)
async def test_generate_voice_does_not_emit_gemini_trace_for_elevenlabs_provider(
    mock_upload_voice_file: AsyncMock,
    mock_call_tts_api: AsyncMock,
    voice_service: VoiceService,
):
    mock_call_tts_api.return_value = (
        b"wav-bytes",
        0.8,
        "audio/mpeg",
        TTS_PROVIDER_ELEVENLABS,
    )
    mock_upload_voice_file.return_value = (
        "https://storage.googleapis.com/test-bucket/voice/202603/voice_test.mp3"
    )

    result = await voice_service.generate_voice(
        text="hello there",
        voice_id="google/Zephyr",
        language="en",
        model="gemini-2.5-flash-tts",
    )

    assert isinstance(result, VoiceGenerationResult)
    assert result.gcs_url == "gs://test-bucket/voice/202603/voice_test.mp3"
    assert (
        result.gcs_http_url
        == "https://storage.googleapis.com/test-bucket/voice/202603/voice_test.mp3"
    )
