"""
CREATED_BY_AGENT: GPT-5.2 (Cursor Cloud Agent)

Text-to-Speech (TTS) wrapper API.

目标：
- 为上层服务提供统一、可扩展的 TTS 调用接口
- 当前仅实现 ElevenLabs（代码库已在使用），后续可无感新增其它 Provider

注意：
- ElevenLabs 官方 Python SDK 的调用为同步 I/O；本模块在 async 场景下使用
  `asyncio.to_thread(...)` 避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from loguru import logger


DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY_BOOST = 0.5


@dataclass(frozen=True)
class TTSRequest:
    text: str
    voice_id: str
    model_id: str
    output_format: str
    language_code: Optional[str] = None
    stability: float = DEFAULT_STABILITY
    similarity_boost: float = DEFAULT_SIMILARITY_BOOST


@dataclass(frozen=True)
class TTSResult:
    audio_bytes: bytes


class TextToSpeechAPI(Protocol):
    async def synthesize(self, request: TTSRequest) -> Optional[TTSResult]:
        ...


def _elevenlabs_supports_language_code(model_id: str) -> bool:
    """
    ElevenLabs 并非所有模型都支持 language_code。

    这里保留与旧逻辑一致的启发式判断，避免引入行为变化：
    - 仅当模型名同时包含 turbo + multilingual 时才透传 language_code
    """

    normalized = model_id.lower()
    return "turbo" in normalized and "multilingual" in normalized


class ElevenLabsTTSAPI:
    """
    ElevenLabs 的 TTS wrapper。

    - synthesize: 文本转语音（返回音频 bytes）
    - get_all_voices / get_shared_voices / get_voice: 语音元数据相关调用
    """

    def __init__(self, *, api_key: str):
        self._client = ElevenLabs(api_key=api_key)

    async def synthesize(self, request: TTSRequest) -> Optional[TTSResult]:
        try:
            voice_settings = VoiceSettings(
                stability=request.stability,
                similarity_boost=request.similarity_boost,
            )

            kwargs: Dict[str, Any] = {
                "text": request.text,
                "voice_id": request.voice_id,
                "model_id": request.model_id,
                "output_format": request.output_format,
                "voice_settings": voice_settings,
            }

            if request.language_code and _elevenlabs_supports_language_code(
                request.model_id
            ):
                kwargs["language_code"] = request.language_code

            response = await asyncio.to_thread(
                self._client.text_to_speech.convert_with_timestamps,
                **kwargs,
            )

            audio_bytes = base64.b64decode(response.audio_base_64)
            if not audio_bytes:
                logger.error("ElevenLabs TTS 返回空音频数据")
                return None

            return TTSResult(audio_bytes=audio_bytes)

        except Exception as e:
            logger.error(f"ElevenLabs TTS 调用失败: {str(e)}")
            logger.exception("ElevenLabs TTS 异常详细信息:")
            return None

    async def get_all_voices(self, *, show_legacy: bool = True) -> Any:
        return await asyncio.to_thread(self._client.voices.get_all, show_legacy=show_legacy)

    async def get_shared_voices(self, **search_params: Any) -> Any:
        return await asyncio.to_thread(self._client.voices.get_shared, **search_params)

    async def get_voice(self, voice_id: str) -> Any:
        return await asyncio.to_thread(self._client.voices.get, voice_id)

