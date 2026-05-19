"""iMate WebSocket 下行语音消息（voice_message）TTS。

适用范围：``/api/v1/chat/ws`` 在 companion 选择 ``reply_modality=voice_message`` 时合成音频；
不含 HTTP legacy（``synthesize_chat_assistant_audio``）与按需 REST TTS。
transcript / voice_id 由调用方解析后传入；本模块不持久化 ``audio_url``。
"""

from __future__ import annotations

from typing import Optional

from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.voice.tts_api import VoiceMessageNarrationMode
from app.services.voice_service import VoiceGenerationResult, VoiceService
from app.utils.timing import log_time


class ChatWsVoiceMessageTtsInput(BaseModel):
    transcript: str


async def synthesize_chat_ws_voice_message(
    inp: ChatWsVoiceMessageTtsInput,
    *,
    db: AsyncSession,
    voice_svc: VoiceService,
    voice_id: str,
    language: str,
    voice_message_narration_mode: VoiceMessageNarrationMode,
) -> Optional[VoiceGenerationResult]:
    transcript = inp.transcript.strip()
    if not transcript:
        return None
    assert voice_id.strip(), "voice_id must be non-empty"
    try:
        with log_time(
            f"chat_ws voice_message TTS: voice_id={voice_id}, "
            f"text_length={len(transcript)}, language={language}"
        ):
            return await voice_svc.generate_voice(
                text=transcript,
                voice_id=voice_id,
                language=language,
                db=db,
                user=None,
                voice_message_narration_mode=voice_message_narration_mode,
            )
    except Exception as e:
        logger.error(f"chat_ws voice_message TTS failed: {e}")
        logger.exception("chat_ws voice_message TTS exception:")
        return None
