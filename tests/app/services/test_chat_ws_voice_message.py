"""Unit tests for WebSocket voice_message TTS service."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.voice.tts_api import VoiceMessageNarrationMode
from app.services.chat_ws_voice_message import (
    ChatWsVoiceMessageTtsInput,
    synthesize_chat_ws_voice_message,
)
from app.services.voice_service import VoiceGenerationResult


@pytest.mark.asyncio
async def test_synthesize_chat_ws_voice_message_empty_transcript_returns_none():
    voice_svc = SimpleNamespace(generate_voice=AsyncMock())
    result = await synthesize_chat_ws_voice_message(
        ChatWsVoiceMessageTtsInput(transcript="   "),
        db=AsyncMock(),
        voice_svc=voice_svc,
        voice_id="voice-1",
        language="en",
        voice_message_narration_mode=VoiceMessageNarrationMode.DIALOGUE_ONLY,
    )
    assert result is None
    voice_svc.generate_voice.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_chat_ws_voice_message_calls_generate_voice_without_user():
    expected = VoiceGenerationResult(
        gcs_url="gs://bucket/voice.mp3",
        gcs_http_url="https://storage.googleapis.com/bucket/voice.mp3",
        duration_seconds=1.5,
    )
    voice_svc = SimpleNamespace(generate_voice=AsyncMock(return_value=expected))
    db = AsyncMock()
    inp = ChatWsVoiceMessageTtsInput(transcript="hello voice")
    result = await synthesize_chat_ws_voice_message(
        inp,
        db=db,
        voice_svc=voice_svc,
        voice_id="voice-1",
        language="en",
        voice_message_narration_mode=VoiceMessageNarrationMode.DIALOGUE_ONLY,
    )
    assert result == expected
    voice_svc.generate_voice.assert_awaited_once_with(
        text="hello voice",
        voice_id="voice-1",
        language="en",
        db=db,
        user=None,
        voice_message_narration_mode=VoiceMessageNarrationMode.DIALOGUE_ONLY,
    )
