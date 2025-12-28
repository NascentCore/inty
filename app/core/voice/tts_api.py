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
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

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

TTS_PROVIDER_GEMINI = "gemini"
TTS_PROVIDER_ELEVENLABS = "elevenlabs"

# Gemini TTS 预置音色列表
# 来源: https://ai.google.dev/gemini-api/docs/speech-generation
GEMINI_PREBUILT_VOICES: List[Dict[str, Any]] = [
    {
        "voice_id": "Zephyr",
        "name": "Zephyr",
        "gender": "female",
        "description": "Bright",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Puck",
        "name": "Puck",
        "gender": "male",
        "description": "Upbeat",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Charon",
        "name": "Charon",
        "gender": "male",
        "description": "Informative",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Kore",
        "name": "Kore",
        "gender": "female",
        "description": "Firm",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Fenrir",
        "name": "Fenrir",
        "gender": "male",
        "description": "Excitable",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Aoede",
        "name": "Aoede",
        "gender": "female",
        "description": "Breezy",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Orus",
        "name": "Orus",
        "gender": "male",
        "description": "Firm",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Leda",
        "name": "Leda",
        "gender": "female",
        "description": "Youthful",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Elf",
        "name": "Elf",
        "gender": "male",
        "description": "Soft",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Orbit",
        "name": "Orbit",
        "gender": "male",
        "description": "Clear",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Altair",
        "name": "Altair",
        "gender": "male",
        "description": "Informative",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Cove",
        "name": "Cove",
        "gender": "male",
        "description": "Calm",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Birch",
        "name": "Birch",
        "gender": "female",
        "description": "Calm",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Maple",
        "name": "Maple",
        "gender": "female",
        "description": "Clear",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Vale",
        "name": "Vale",
        "gender": "male",
        "description": "Gentle",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Breeze",
        "name": "Breeze",
        "gender": "female",
        "description": "Animated",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Juniper",
        "name": "Juniper",
        "gender": "female",
        "description": "Open",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Solaris",
        "name": "Solaris",
        "gender": "male",
        "description": "Smooth",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Vega",
        "name": "Vega",
        "gender": "female",
        "description": "Raspy",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Nova",
        "name": "Nova",
        "gender": "male",
        "description": "Even",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Stella",
        "name": "Stella",
        "gender": "female",
        "description": "Spirited",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Eclipse",
        "name": "Eclipse",
        "gender": "female",
        "description": "Assured",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Dawn",
        "name": "Dawn",
        "gender": "female",
        "description": "Composed",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Ember",
        "name": "Ember",
        "gender": "male",
        "description": "Even",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Shade",
        "name": "Shade",
        "gender": "male",
        "description": "Measured",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Cosmos",
        "name": "Cosmos",
        "gender": "male",
        "description": "Relaxed",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Saga",
        "name": "Saga",
        "gender": "female",
        "description": "Poised",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Aurora",
        "name": "Aurora",
        "gender": "female",
        "description": "Warm",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Summit",
        "name": "Summit",
        "gender": "male",
        "description": "Direct",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
    {
        "voice_id": "Meadow",
        "name": "Meadow",
        "gender": "female",
        "description": "Serene",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
    },
]

# 预计算 Gemini 音色名称集合，用于快速查找
_GEMINI_VOICE_NAMES: Set[str] = {v["voice_id"] for v in GEMINI_PREBUILT_VOICES}


def is_gemini_voice(voice_id: Optional[str]) -> bool:
    """判断给定的 voice_id 是否为 Gemini TTS 预置音色"""
    if not voice_id:
        return False
    return voice_id in _GEMINI_VOICE_NAMES


def get_gemini_voices() -> List[Dict[str, Any]]:
    """获取 Gemini TTS 预置音色列表（返回副本，避免外部修改）"""
    return [v.copy() for v in GEMINI_PREBUILT_VOICES]


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
    async def synthesize(self, request: TTSRequest) -> Optional[TTSResult]: ...


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

    优先使用精确匹配（is_gemini_voice），回退到启发式判断（纯字母 + 长度限制）。
    """
    if not voice_id:
        return False
    if is_gemini_voice(voice_id):
        return True
    return voice_id.isalpha() and 2 <= len(voice_id) <= 32


class GeminiTTSAPI:
    """
    Gemini TTS wrapper（基于 google-genai 官方 demo）。

    注意：目前 Gemini TTS 通常返回裸 PCM（如 audio/L16;rate=24000），本实现会自动封装为 WAV。
    认证方式与 LiveChatService 统一，使用 app.gcp_service_account_key 配置。
    """

    def __init__(
        self,
        *,
        model: str = DEFAULT_GEMINI_TTS_MODEL,
        default_voice_name: str = DEFAULT_GEMINI_TTS_VOICE_NAME,
        temperature: float = DEFAULT_GEMINI_TTS_TEMPERATURE,
    ):
        self._model = model
        self._default_voice_name = default_voice_name
        self._temperature = temperature
        # 延迟初始化：CI/本地可能没有凭据；此时直接回退 ElevenLabs，
        # 不应在 import / app 启动阶段硬失败。
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> Optional[genai.Client]:
        if self._client is not None:
            return self._client

        try:
            # 统一使用 app.gcp_service_account_key 配置进行认证
            # 与 LiveChatService 保持一致
            from app.core.config import global_config_loaded_from_config_yaml

            gcp_key_path = (
                global_config_loaded_from_config_yaml.app.gcp_service_account_key
            )
            if gcp_key_path and os.path.exists(gcp_key_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_key_path
                logger.debug(f"Gemini TTS 设置 GCP 凭证: {gcp_key_path}")

            gemini_live_config = global_config_loaded_from_config_yaml.gemini_live
            self._client = genai.Client(
                vertexai=True,
                project=gemini_live_config.project_id,
                location=gemini_live_config.location,
            )
            logger.info(
                f"Gemini TTS 客户端已初始化 - project: {gemini_live_config.project_id}, "
                f"location: {gemini_live_config.location}"
            )
            return self._client
        except Exception as e:
            logger.warning(f"Gemini TTS client 初始化失败: {str(e)}")
            return None

    async def synthesize(self, request: TTSRequest) -> Optional[TTSResult]:
        client = self._get_client()
        if client is None:
            logger.info("Gemini TTS 未配置可用凭据，跳过并回退到其它 TTS provider")
            return None

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
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
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
                for chunk in client.models.generate_content_stream(
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

            return TTSResult(
                audio_bytes=audio_bytes,
                mime_type=mime_type or "application/octet-stream",
            )

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
        return await asyncio.to_thread(
            self._client.voices.get_all, show_legacy=show_legacy
        )

    async def get_shared_voices(self, **search_params: Any) -> Any:
        return await asyncio.to_thread(self._client.voices.get_shared, **search_params)

    async def get_voice(self, voice_id: str) -> Any:
        return await asyncio.to_thread(self._client.voices.get, voice_id)
