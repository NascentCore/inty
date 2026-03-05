"""
CREATED_BY_AGENT
VoiceService provider/model 路由止血测试。

关键步骤总结：
1) 验证 google/ 音色在 model=None 且无 user/db 时，仍选择 Gemini 模型（不再串到 ElevenLabs）。
2) 验证显式传入 provider 不匹配模型时立即失败（Fail Loud），且不会发起 TTS 调用。
3) 验证 Gemini 失败回退 ElevenLabs 时，fallback request 会重绑 ElevenLabs 的默认 model/voice。
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import global_config_loaded_from_config_yaml as global_config
from app.core.voice.tts_api import TTS_PROVIDER_ELEVENLABS, TTSResult
from app.services.voice_service import VoiceService


@pytest.fixture
def voice_service() -> VoiceService:
    service = VoiceService()
    service.config.enabled = True
    return service


@pytest.mark.asyncio
@patch.object(VoiceService, "_call_tts_api", new_callable=AsyncMock)
@patch(
    "app.services.voice_service.GCSService.upload_voice_file", new_callable=AsyncMock
)
async def test_generate_voice_google_voice_without_user_uses_gemini_default_model(
    mock_upload_voice_file: AsyncMock,
    mock_call_tts_api: AsyncMock,
    voice_service: VoiceService,
):
    mock_call_tts_api.return_value = (
        b"wav-bytes",
        0.7,
        "audio/wav",
        "gemini",
    )
    mock_upload_voice_file.return_value = (
        "https://storage.googleapis.com/test-bucket/voice/202603/voice_test.wav"
    )

    await voice_service.generate_voice(
        text="hello",
        voice_id="google/Zephyr",
        language="en",
        model=None,
    )

    called_args = mock_call_tts_api.await_args.args
    assert called_args[2] == global_config.agent.free_user_chat_tts_model


@pytest.mark.asyncio
@patch.object(VoiceService, "_call_tts_api", new_callable=AsyncMock)
async def test_generate_voice_rejects_explicit_mismatched_model(
    mock_call_tts_api: AsyncMock,
    voice_service: VoiceService,
):
    with pytest.raises(ValueError, match="TTS model/provider mismatch"):
        await voice_service.generate_voice(
            text="hello",
            voice_id="google/Zephyr",
            language="en",
            model="eleven_flash_v2_5",
        )

    assert mock_call_tts_api.await_count == 0


@pytest.mark.asyncio
@patch.object(VoiceService, "_calculate_audio_duration", return_value=1.0)
@patch("app.services.voice_service.ElevenLabsTTSAPI.synthesize", new_callable=AsyncMock)
@patch("app.services.voice_service.GeminiTTSAPI.synthesize", new_callable=AsyncMock)
@patch(
    "app.services.voice_service.GeminiTTSAPI.synthesize_with_roleplay_prompt",
    new_callable=AsyncMock,
)
async def test_call_tts_api_rebinds_model_and_voice_when_fallback_to_elevenlabs(
    mock_gemini_prompted: AsyncMock,
    mock_gemini_synthesize: AsyncMock,
    mock_elevenlabs_synthesize: AsyncMock,
    _mock_calculate_audio_duration,
    voice_service: VoiceService,
):
    mock_gemini_prompted.return_value = None
    mock_gemini_synthesize.return_value = None
    mock_elevenlabs_synthesize.return_value = TTSResult(
        audio_bytes=b"fallback-audio",
        mime_type="audio/mpeg",
    )

    result = await voice_service._call_tts_api(
        text="hello",
        voice_id="google/Zephyr",
        model=global_config.agent.free_user_chat_tts_model,
        language="en",
    )

    assert result is not None
    assert result[3] == TTS_PROVIDER_ELEVENLABS
    fallback_request = mock_elevenlabs_synthesize.await_args.args[0]
    assert fallback_request.voice_id == voice_service.config.voice_id
    assert fallback_request.model_id == voice_service.config.model


@pytest.mark.asyncio
@patch("app.services.voice_service.ElevenLabsTTSAPI.synthesize", new_callable=AsyncMock)
async def test_call_tts_api_rejects_gemini_model_on_elevenlabs_path(
    mock_elevenlabs_synthesize: AsyncMock,
    voice_service: VoiceService,
):
    with pytest.raises(ValueError, match="TTS model/provider mismatch"):
        await voice_service._call_tts_api(
            text="hello",
            voice_id="11labs/JBFqnCBsd6RMkjVDRZzb",
            model="gemini-2.5-pro-tts",
            language="en",
        )

    assert mock_elevenlabs_synthesize.await_count == 0
