"""Tests for Gemini TTS voice result GCS URL fields."""

import types
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


def test_build_voice_gcs_urls_accepts_gs_url() -> None:
    gcs_url, gcs_http_url = build_voice_gcs_urls("gs://test-bucket/voice/x.wav")
    assert gcs_url == "gs://test-bucket/voice/x.wav"
    assert gcs_http_url == "https://storage.googleapis.com/test-bucket/voice/x.wav"


def test_build_voice_gcs_urls_preserves_file_uri_when_fake_gcs(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    import app.external_services.gcs as gcs_module

    base = tmp_path.resolve()
    file_path = base / "test-bucket" / "voice" / "202605" / "x.mp3"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"x")
    storage_url = file_path.as_uri()
    merged = types.SimpleNamespace(
        gcs=types.SimpleNamespace(
            bucket="test-bucket",
            use_fake_gcs=True,
            fake_gcs_base_dir=str(base),
        )
    )
    monkeypatch.setattr(
        gcs_module,
        "global_config_loaded_from_config_yaml",
        merged,
        raising=True,
    )
    gcs_url, gcs_http_url = build_voice_gcs_urls(storage_url)
    assert gcs_url == "gs://test-bucket/voice/202605/x.mp3"
    assert gcs_http_url == storage_url


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
