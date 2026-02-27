from types import SimpleNamespace

from google.genai import types

from app.services.live_chat_service import LiveChatService


def _build_service_with_language_config() -> LiveChatService:
    service = LiveChatService()
    service._config = SimpleNamespace(
        default_voice="Zephyr",
        input_transcription=True,
        output_transcription=True,
        send_sample_rate=16000,
        speech_language_code="en-US",
        response_language_name="English",
    )
    return service


def test_build_system_instruction_includes_english_only_policy():
    service = _build_service_with_language_config()

    instruction = service._build_system_instruction(
        agent_data={
            "personality": "Friendly and warm.",
            "scenario": "Daily chat.",
            "intro": "A supportive companion.",
        },
        history_messages=[],
    )

    assert "Language policy" in instruction
    assert "ONLY in English" in instruction
    assert "Never switch to any other language" in instruction


def test_build_live_config_sets_speech_language_code_when_supported():
    service = _build_service_with_language_config()

    live_config = service._build_live_config(
        voice_id="Zephyr",
        agent_gender="FEMALE",
        system_instruction="test",
    )

    assert live_config.speech_config is not None
    assert live_config.speech_config.voice_config is not None
    assert live_config.speech_config.voice_config.prebuilt_voice_config is not None
    assert (
        live_config.speech_config.voice_config.prebuilt_voice_config.voice_name
        == "Zephyr"
    )

    if "language_code" in getattr(types.SpeechConfig, "model_fields", {}):
        assert live_config.speech_config.language_code == "en-US"
    else:
        assert not hasattr(live_config.speech_config, "language_code")


def test_build_live_config_accepts_google_prefixed_voice_id():
    """带 google/ 前缀的 voice_id 应解析为 raw 名字传给 Gemini Live。"""
    service = _build_service_with_language_config()

    live_config = service._build_live_config(
        voice_id="google/Zephyr",
        agent_gender="FEMALE",
        system_instruction="test",
    )

    assert live_config.speech_config is not None
    assert (
        live_config.speech_config.voice_config.prebuilt_voice_config.voice_name
        == "Zephyr"
    )
