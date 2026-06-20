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

from app.core.config import (
    global_config_loaded_from_config_yaml as global_config,
)
from app.core.voice.tts_api import (
    TTS_PROVIDER_ELEVENLABS,
    TTSResult,
    VoiceMessageNarrationMode,
)
from app.external_services.fakes.tts import FakeTextToSpeechAPI
from app.services.voice_service import (
    VoiceService,
    get_voice_message_narration_mode_from_agent_settings,
)


@pytest.fixture
def voice_service() -> VoiceService:
    previous = global_config.tts.use_fake_tts
    global_config.tts.use_fake_tts = False
    try:
        service = VoiceService()
        service.config.enabled = True
        yield service
    finally:
        global_config.tts.use_fake_tts = previous


@pytest.mark.asyncio
@patch.object(VoiceService, "_call_tts_api", new_callable=AsyncMock)
@patch(
    "app.services.voice_service.GCSService.upload_voice_file",
    new_callable=AsyncMock,
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

    called_kwargs = mock_call_tts_api.await_args.kwargs
    assert (
        called_kwargs["model"] == global_config.agent.free_user_chat_tts_model
    )


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
@patch.object(VoiceService, "_call_tts_api", new_callable=AsyncMock)
async def test_generate_voice_rejects_unknown_model_even_if_prefix_matches(
    mock_call_tts_api: AsyncMock,
    voice_service: VoiceService,
):
    with pytest.raises(ValueError, match="TTS model/provider mismatch"):
        await voice_service.generate_voice(
            text="hello",
            voice_id="google/Zephyr",
            language="en",
            model="gemini-unknown-tts",
        )

    assert mock_call_tts_api.await_count == 0


@pytest.mark.asyncio
@patch.object(VoiceService, "_calculate_audio_duration", return_value=1.0)
@patch(
    "app.services.voice_service.ElevenLabsTTSAPI.synthesize",
    new_callable=AsyncMock,
)
@patch(
    "app.services.voice_service.GeminiTTSAPI.synthesize", new_callable=AsyncMock
)
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
        agent_gender=None,
        gemini_source_model=None,
    )

    assert result is not None
    assert result[3] == TTS_PROVIDER_ELEVENLABS
    fallback_request = mock_elevenlabs_synthesize.await_args.args[0]
    assert fallback_request.voice_id == voice_service.config.voice_id
    assert fallback_request.model_id == voice_service.config.model


@pytest.mark.asyncio
@patch(
    "app.services.voice_service.ElevenLabsTTSAPI.synthesize",
    new_callable=AsyncMock,
)
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
            agent_gender=None,
            gemini_source_model=None,
        )

    assert mock_elevenlabs_synthesize.await_count == 0


@pytest.mark.asyncio
async def test_call_tts_api_uses_fake_tts_when_test_config_enables_it():
    previous = global_config.tts.use_fake_tts
    global_config.tts.use_fake_tts = True
    try:
        service = VoiceService()

        result = await service._call_tts_api(
            text="hello",
            voice_id="11labs/JBFqnCBsd6RMkjVDRZzb",
            model=service.config.model,
            language="en",
            agent_gender=None,
            gemini_source_model=None,
        )
    finally:
        global_config.tts.use_fake_tts = previous

    assert isinstance(service.tts_api, FakeTextToSpeechAPI)
    assert result is not None
    assert result[2] == "audio/wav"
    assert result[3] == TTS_PROVIDER_ELEVENLABS


@pytest.mark.asyncio
@patch(
    "app.services.voice_service.GeminiTTSAPI.synthesize_with_roleplay_prompt",
    new_callable=AsyncMock,
)
async def test_call_tts_api_passes_voice_message_narration_mode_to_gemini(
    mock_gemini_prompted: AsyncMock,
    voice_service: VoiceService,
):
    mock_gemini_prompted.return_value = TTSResult(
        audio_bytes=b"gemini-audio",
        mime_type="audio/wav",
    )

    await voice_service._call_tts_api(
        text='(whispers) "hello"',
        voice_id="google/Zephyr",
        model=global_config.agent.free_user_chat_tts_model,
        language="en",
        voice_message_narration_mode=VoiceMessageNarrationMode.DIALOGUE_AND_STAGE_DIRECTIONS,
        agent_gender=None,
        gemini_source_model=None,
    )

    request = mock_gemini_prompted.await_args.args[0]
    assert (
        request.voice_message_narration_mode
        == VoiceMessageNarrationMode.DIALOGUE_AND_STAGE_DIRECTIONS
    )


def test_get_voice_message_narration_mode_falls_back_to_tts_config():
    previous = global_config.tts.voice_message_narration_mode
    try:
        global_config.tts.voice_message_narration_mode = (
            VoiceMessageNarrationMode.DIALOGUE_AND_STAGE_DIRECTIONS
        )
        mode = get_voice_message_narration_mode_from_agent_settings(None)
        assert mode == VoiceMessageNarrationMode.DIALOGUE_AND_STAGE_DIRECTIONS
    finally:
        global_config.tts.voice_message_narration_mode = previous


@patch.object(VoiceService, "_calculate_audio_duration", return_value=1.2)
@patch(
    "app.services.voice_service.ElevenLabsTTSAPI.convert_with_voice_changer",
    new_callable=AsyncMock,
)
@patch(
    "app.services.voice_service.GeminiTTSAPI.synthesize_with_full_dialogue_prompt",
    new_callable=AsyncMock,
)
async def test_call_tts_api_uses_gemini_then_voice_changer_for_elevenlabs_voice(
    mock_full_dialogue: AsyncMock,
    mock_voice_changer: AsyncMock,
    _mock_calculate_audio_duration,
    voice_service: VoiceService,
):
    old_flag = (
        global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
    )
    global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate = (
        True
    )
    try:
        mock_full_dialogue.return_value = TTSResult(
            audio_bytes=b"gemini-audio",
            mime_type="audio/wav",
        )
        mock_voice_changer.return_value = TTSResult(
            audio_bytes=b"converted-audio",
            mime_type="audio/mpeg",
        )

        text = '(She smiles) "Hello there."'
        result = await voice_service._call_tts_api(
            text=text,
            voice_id="11labs/JBFqnCBsd6RMkjVDRZzb",
            model=voice_service.config.model,
            language="en",
            agent_gender="MALE",
            gemini_source_model="gemini-2.5-flash-tts",
        )

        assert result is not None
        assert result[0] == b"converted-audio"
        assert result[3] == TTS_PROVIDER_ELEVENLABS

        source_req = mock_full_dialogue.await_args.args[0]
        assert source_req.voice_id == "google/Puck"
        assert source_req.text == text

        changer_kwargs = mock_voice_changer.await_args.kwargs
        assert (
            changer_kwargs["target_voice_id"] == "11labs/JBFqnCBsd6RMkjVDRZzb"
        )
        assert (
            changer_kwargs["model_id"]
            == voice_service.config.voice_change_model
        )
    finally:
        global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate = (
            old_flag
        )


@pytest.mark.asyncio
@patch.object(VoiceService, "_calculate_audio_duration", return_value=1.0)
@patch(
    "app.services.voice_service.ElevenLabsTTSAPI.convert_with_voice_changer",
    new_callable=AsyncMock,
)
@patch(
    "app.services.voice_service.GeminiTTSAPI.synthesize_with_roleplay_prompt",
    new_callable=AsyncMock,
)
async def test_call_tts_api_does_not_use_voice_changer_for_gemini_voice(
    mock_gemini_prompted: AsyncMock,
    mock_voice_changer: AsyncMock,
    _mock_calculate_audio_duration,
    voice_service: VoiceService,
):
    old_flag = (
        global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
    )
    global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate = (
        True
    )
    try:
        mock_gemini_prompted.return_value = TTSResult(
            audio_bytes=b"gemini-voice",
            mime_type="audio/wav",
        )
        result = await voice_service._call_tts_api(
            text="hello",
            voice_id="google/Zephyr",
            model=global_config.agent.free_user_chat_tts_model,
            language="en",
            agent_gender="FEMALE",
            gemini_source_model=None,
        )
        assert result is not None
        assert result[3] == "gemini"
        assert mock_voice_changer.await_count == 0
    finally:
        global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate = (
            old_flag
        )


@pytest.mark.asyncio
@patch.object(VoiceService, "_call_tts_api", new_callable=AsyncMock)
@patch(
    "app.services.voice_service.GCSService.upload_voice_file",
    new_callable=AsyncMock,
)
async def test_generate_voice_keeps_original_text_for_voice_changer_path(
    mock_upload_voice_file: AsyncMock,
    mock_call_tts_api: AsyncMock,
    voice_service: VoiceService,
):
    old_flag = (
        global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
    )
    global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate = (
        True
    )
    try:
        raw_text = '(whispers) "Hi there."'
        mock_call_tts_api.return_value = (
            b"audio",
            0.8,
            "audio/mpeg",
            TTS_PROVIDER_ELEVENLABS,
        )
        mock_upload_voice_file.return_value = "https://storage.googleapis.com/test-bucket/voice/202603/voice_test.mp3"

        await voice_service.generate_voice(
            text=raw_text,
            voice_id="11labs/JBFqnCBsd6RMkjVDRZzb",
            language="en",
            agent_gender="MALE",
        )

        called_kwargs = mock_call_tts_api.await_args.kwargs
        assert called_kwargs["text"] == raw_text
    finally:
        global_config.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate = (
            old_flag
        )
