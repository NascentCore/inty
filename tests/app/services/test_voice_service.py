import pytest

# CREATED_BY_AGENT

from app.services.voice_service import (
    GEMINI_TO_ELEVEN_VOICE_ID,
    VoiceProvider,
    VoiceService,
)


class _DummyVoicesAPI:
    def get_all(self, **kwargs):
        return type("Resp", (), {"voices": []})()

    def get_shared(self, **kwargs):
        return type("Resp", (), {"voices": []})()

    def get(self, voice_id):
        class _Voice:
            def model_dump(self):
                return {"voice_id": voice_id}

        return _Voice()


class _DummyElevenLabs:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.voices = _DummyVoicesAPI()


@pytest.fixture
def voice_service(monkeypatch):
    monkeypatch.setattr(
        "app.services.voice_service.ElevenLabs", _DummyElevenLabs
    )
    service = VoiceService()
    # 测试中启用两种语音提供商，便于覆盖逻辑
    service.config.enabled = True
    service.gemini_config.enabled = True
    return service


def test_resolve_voice_selection_with_gemini_prefix(voice_service):
    selection = voice_service._resolve_voice_selection("gemini:Kore", "female")
    assert selection.gemini_voice_name == "Kore"
    assert (
        selection.provider_voice_id(VoiceProvider.GEMINI) == "gemini:kore"
    )
    assert (
        selection.elevenlabs_voice_id
        == GEMINI_TO_ELEVEN_VOICE_ID["kore"]
    )


def test_resolve_voice_selection_from_elevenlabs_id(voice_service):
    elevenlabs_voice = "rHWSYoq8UlV0YIBKMryp"
    selection = voice_service._resolve_voice_selection(
        elevenlabs_voice, "MALE"
    )
    assert selection.gemini_voice_name == "charon"
    assert (
        selection.provider_voice_id(VoiceProvider.ELEVENLABS)
        == elevenlabs_voice
    )
    assert selection.elevenlabs_voice_id == elevenlabs_voice


def test_build_provider_sequence_respects_flags(voice_service):
    voice_service.gemini_config.enabled = True
    voice_service.config.enabled = True
    assert voice_service._build_provider_sequence() == [
        VoiceProvider.GEMINI,
        VoiceProvider.ELEVENLABS,
    ]

    voice_service.gemini_config.enabled = False
    assert voice_service._build_provider_sequence() == [
        VoiceProvider.ELEVENLABS
    ]


def test_normalize_gemini_audio_returns_wav(voice_service):
    pcm_bytes = (b"\x00\x00\x10\x00") * 50  # 简单的 PCM 采样
    audio_bytes, duration, content_type, extension = (
        voice_service.gemini_provider.normalize_audio(
            pcm_bytes, "audio/L16;rate=8000"
        )
    )

    assert audio_bytes.startswith(b"RIFF")
    assert content_type == "audio/wav"
    assert extension == ".wav"
    assert duration > 0
