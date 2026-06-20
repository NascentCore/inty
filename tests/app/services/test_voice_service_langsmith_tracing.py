from types import SimpleNamespace

import pytest

from app.services.voice_service import (
    VoiceGenerationResult,
    VoiceService,
    _process_outputs_call_tts_api,
    _process_outputs_generate_voice,
    _process_outputs_tts_fallback,
)


def test_process_outputs_generate_voice_success() -> None:
    output = VoiceGenerationResult(
        gcs_url="gs://bucket/voice.wav",
        gcs_http_url="https://storage.googleapis.com/bucket/voice.wav",
        duration_seconds=1.25,
    )
    summary = _process_outputs_generate_voice(output)
    assert summary == {
        "status": "success",
        "gcs_url": "gs://bucket/voice.wav",
        "gcs_http_url": "https://storage.googleapis.com/bucket/voice.wav",
        "duration_seconds": 1.25,
    }


def test_process_outputs_generate_voice_none() -> None:
    summary = _process_outputs_generate_voice(None)
    assert summary == {"status": "no_result"}


def test_process_outputs_tts_fallback_success() -> None:
    summary = _process_outputs_tts_fallback((b"audio", "audio/mpeg"))
    assert summary == {
        "status": "success",
        "audio_bytes_len": 5,
        "mime_type": "audio/mpeg",
    }


def test_process_outputs_call_tts_api_success() -> None:
    summary = _process_outputs_call_tts_api(
        (b"audio", 2.5, "audio/wav", "gemini")
    )
    assert summary == {
        "status": "success",
        "audio_bytes_len": 5,
        "duration_seconds": 2.5,
        "mime_type": "audio/wav",
        "provider_used": "gemini",
    }


@pytest.mark.asyncio
async def test_generate_voice_empty_text_records_failure_reason(
    monkeypatch,
) -> None:
    service = VoiceService()
    service.config.enabled = True
    run = SimpleNamespace(metadata={})

    monkeypatch.setattr(
        "app.services.voice_service.get_current_run_tree", lambda: run
    )

    result = await service.generate_voice(text="   ")

    assert result is None
    assert run.metadata["status"] == "no_result"
    assert run.metadata["failure_reason"] == "empty_input_text"
