"""Tests for Gemini TTS voice result GCS URL fields."""

import types
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.voice.tts_api import TTS_PROVIDER_ELEVENLABS, TTS_PROVIDER_GEMINI
from app.services import voice_service as voice_service_mod
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


def test_build_voice_gcs_urls_preserves_file_uri_under_fake_gcs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import app.external_services.gcs as gcs_module

    store_dir = tmp_path / "fake_store"
    obj_path = store_dir / "mybucket" / "voice" / "out.mp3"
    obj_path.parent.mkdir(parents=True)
    obj_path.write_bytes(b"\xff\xfb")
    file_uri = obj_path.resolve().as_uri()
    cfg = types.SimpleNamespace(
        gcs=types.SimpleNamespace(
            use_fake_gcs=True,
            fake_gcs_base_dir=str(store_dir.resolve()),
        )
    )
    monkeypatch.setattr(
        voice_service_mod,
        "global_config_loaded_from_config_yaml",
        cfg,
        raising=True,
    )
    monkeypatch.setattr(
        gcs_module,
        "global_config_loaded_from_config_yaml",
        cfg,
        raising=True,
    )
    gcs_url, gcs_http_url = build_voice_gcs_urls(file_uri)
    assert gcs_http_url == file_uri
    assert gcs_url == "gs://mybucket/voice/out.mp3"


def test_build_voice_gcs_urls_rejects_file_uri_without_fake_gcs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store_dir = tmp_path / "fake_store"
    obj_path = store_dir / "mybucket" / "voice" / "out.mp3"
    obj_path.parent.mkdir(parents=True)
    obj_path.write_bytes(b"x")
    file_uri = obj_path.resolve().as_uri()
    monkeypatch.setattr(
        voice_service_mod,
        "global_config_loaded_from_config_yaml",
        types.SimpleNamespace(
            gcs=types.SimpleNamespace(
                use_fake_gcs=False,
                fake_gcs_base_dir=str(store_dir.resolve()),
            )
        ),
        raising=True,
    )
    with pytest.raises(ValueError, match="use_fake_gcs is false"):
        build_voice_gcs_urls(file_uri)


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
