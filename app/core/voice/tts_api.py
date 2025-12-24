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
import os
import struct
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

import google.genai as genai
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from google.genai import types
from loguru import logger


DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY_BOOST = 0.5
DEFAULT_GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_GEMINI_TTS_VOICE_NAME = "Zephyr"
DEFAULT_GEMINI_TTS_TEMPERATURE = 1.3


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
    mime_type: str


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


def _parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """
    从 Gemini 的音频 mime_type（例如 "audio/L16;rate=24000"）解析采样率与采样位数。
    """

    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            rate_str = param.split("=", 1)[1] if "=" in param else ""
            if rate_str.isdigit():
                rate = int(rate_str)
        elif param.startswith("audio/L"):
            suffix = param.split("audio/L", 1)[1]
            if suffix.isdigit():
                bits_per_sample = int(suffix)
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def _pcm_to_wav(audio_data: bytes, *, mime_type: str) -> bytes:
    """
    将 Gemini 返回的裸 PCM 数据包装为 WAV（补齐 header）。
    """

    parameters = _parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1

    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,  # PCM
        1,  # AudioFormat: PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + audio_data


def _looks_like_gemini_voice_name(voice_id: str) -> bool:
    """
    兼容旧字段：如果上层仍沿用 voice_id 字段，但存的是 Gemini 预置音色名（如 Zephyr），
    这里允许直接复用；否则回退到默认音色。
    """

    if not voice_id:
        return False
    return voice_id.isalpha() and 2 <= len(voice_id) <= 32


def _get_gemini_api_key_from_env() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


class GeminiTTSAPI:
    """
    Gemini TTS wrapper（基于 google-genai 官方 demo）。

    注意：目前 Gemini TTS 通常返回裸 PCM（如 audio/L16;rate=24000），本实现会自动封装为 WAV。
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GEMINI_TTS_MODEL,
        default_voice_name: str = DEFAULT_GEMINI_TTS_VOICE_NAME,
        temperature: float = DEFAULT_GEMINI_TTS_TEMPERATURE,
    ):
        self._api_key = api_key or _get_gemini_api_key_from_env()
        self._model = model
        self._default_voice_name = default_voice_name
        self._temperature = temperature
        self._client = genai.Client(api_key=self._api_key) if self._api_key else genai.Client()

    async def synthesize(self, request: TTSRequest) -> Optional[TTSResult]:
        voice_name = (
            request.voice_id
            if _looks_like_gemini_voice_name(request.voice_id)
            else self._default_voice_name
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=request.text)],
            )
        ]

        config = types.GenerateContentConfig(
            temperature=self._temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )

        try:
            audio_chunks: list[bytes] = []
            mime_type: Optional[str] = None

            # google-genai 的流式接口是同步迭代，这里放到线程池避免阻塞 event loop
            def _sync_collect() -> Tuple[bytes, Optional[str]]:
                collected: list[bytes] = []
                mt: Optional[str] = None
                for chunk in self._client.models.generate_content_stream(
                    model=self._model,
                    contents=contents,
                    config=config,
                ):
                    if (
                        chunk.candidates is None
                        or not chunk.candidates
                        or chunk.candidates[0].content is None
                        or chunk.candidates[0].content.parts is None
                        or not chunk.candidates[0].content.parts
                    ):
                        continue

                    part0 = chunk.candidates[0].content.parts[0]
                    inline = getattr(part0, "inline_data", None)
                    if not inline or not getattr(inline, "data", None):
                        continue

                    if mt is None and getattr(inline, "mime_type", None):
                        mt = inline.mime_type
                    collected.append(inline.data)
                return b"".join(collected), mt

            audio_bytes, mime_type = await asyncio.to_thread(_sync_collect)

            if not audio_bytes:
                logger.error("Gemini TTS 返回空音频数据")
                return None

            if mime_type and mime_type.startswith("audio/L"):
                audio_bytes = _pcm_to_wav(audio_bytes, mime_type=mime_type)
                mime_type = "audio/wav"

            return TTSResult(audio_bytes=audio_bytes, mime_type=mime_type or "application/octet-stream")

        except Exception as e:
            logger.error(f"Gemini TTS 调用失败: {str(e)}")
            logger.exception("Gemini TTS 异常详细信息:")
            return None


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

            return TTSResult(audio_bytes=audio_bytes, mime_type="audio/mpeg")

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

