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
from enum import StrEnum
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from google.genai import types
from langsmith import traceable
from loguru import logger

from app.core.companion_harness.providers.gemini import (
    GeminiClientOptions,
    get_gemini_client as get_kernel_gemini_client,
)
from app.utils.models_catalog import ModelBuilder

DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY_BOOST = 0.5
DEFAULT_GEMINI_TTS_MODEL = "gemini-2.5-flash-tts"
DEFAULT_GEMINI_TTS_VOICE_NAME = "Zephyr"
DEFAULT_GEMINI_TTS_TEMPERATURE = 1.3

TTS_PROVIDER_GEMINI = "gemini"
TTS_PROVIDER_ELEVENLABS = "elevenlabs"

# 对外 voice_id 前缀（列表返回、客户端存储与解析一致）
VOICE_ID_PREFIX_GEMINI = ModelBuilder.GOOGLE.value
VOICE_ID_PREFIX_ELEVENLABS = ModelBuilder.ELEVENLABS.value

VOICE_MESSAGE_NARRATION_MODE_SETTINGS_KEY = "voice_message_narration_mode"


class VoiceMessageNarrationMode(StrEnum):
    DIALOGUE_ONLY = "dialogue_only"
    DIALOGUE_AND_STAGE_DIRECTIONS = "dialogue_and_stage_directions"


# Prompted TTS: instruction so Gemini acts as voice actor; parentheticals = stage directions.
# Enhanced per https://ai.google.dev/gemini-api/docs/speech-generation#prompting-guide
# (Director's Notes: natural, expressive delivery; transcript rules preserved from speech_gen.)
TTS_ROLEPLAY_INSTRUCTION = """
You are an erotic movie voice actor.
You are acting as a fictional character in an intimate scene.
You are given stage directions and dialogue.
You should speak the dialogues based on the stage directions.
"""

TTS_FULL_NARRATION_INSTRUCTION = """
You are an erotic movie voice actor.
You are acting as a fictional character in an intimate scene.
Narrate the full script exactly as written, including both dialogue and any stage directions in parentheses.
"""
# Full-dialogue conversion for Gemini->ElevenLabs voice changing:
# - no text filtering
# - no stage-direction/dialogue splitting
TTS_FULL_DIALOGUE_CONVERSION_INSTRUCTION = """
You are an erotic movie voice actor.
You are acting as a fictional character in an intimate scene.
You are given a full dialogue script that may include stage directions and spoken lines.
Convert the full script into natural spoken audio in one pass.
Use the original script as provided without splitting parts into separate sections.
"""

IMATE_GENDER_TO_DEFAULT_GEMINI_SOURCE_VOICE: Dict[str, str] = {
    "MALE": "Puck",
    "FEMALE": "Zephyr",
    "OTHER": DEFAULT_GEMINI_TTS_VOICE_NAME,
}
# How the per-voice "keywords" were generated (for reference):
#
# 1. Pulled official samples from the Chirp 3 HD doc page (all 30 voice .wav URLs).
# 2. Analyzed each clip; per voice we computed:
#    - Duration → proxy for pacing (fast / medium / slow)
#    - Estimated pitch (F0) via autocorrelation → low vs high pitch
#    - Spectral centroid → darker/warmer vs brighter/clearer tone
#    - RMS energy → gentle vs strong presence
#    - Dynamic range (P90–P10 energy) → steady vs expressive variation
# 3. Converted numbers to keywords: compared voices (quartiles), then mapped to words, e.g.:
#    - high centroid + high F0 → bright, high-pitched
#    - low centroid + low F0 → deep, warm
#    - short duration → fast pacing
#    - high dynamic range → expressive; low → steady
# 4. Built a use-case shortlist and matched tags to scenario intent:
#    - support → clearer + steadier
#    - storytelling → more expressive
#    - wellness → softer + slower, etc.

# Gemini TTS 预置音色列表
# 来源: https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd (Chirp 3: HD voices)
_GCS_VOICE_PREVIEW_BASE = (
    "https://storage.googleapis.com/inty-static/voice_previews/gemini"
)

# 来源：https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd
# 其中 keywords 使用 Cursor Agent 云端自主阅读完成，采用了对音频直接进行分析的方式
GEMINI_PREBUILT_VOICES: List[Dict[str, Any]] = [
    {
        "voice_id": "Zephyr",
        "name": "Zephyr",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Zephyr.mp3",
        "keywords": ["balanced", "fast pacing", "gentle", "steady"],
    },
    {
        "voice_id": "Puck",
        "name": "Puck",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Puck.mp3",
        "keywords": ["clear", "medium pacing", "natural", "smooth"],
    },
    {
        "voice_id": "Charon",
        "name": "Charon",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Charon.mp3",
        "keywords": ["deep", "warm", "fast pacing", "strong", "expressive"],
    },
    {
        "voice_id": "Kore",
        "name": "Kore",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Kore.mp3",
        "keywords": [
            "bright",
            "high-pitched",
            "slow pacing",
            "natural",
            "smooth",
        ],
    },
    {
        "voice_id": "Fenrir",
        "name": "Fenrir",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Fenrir.mp3",
        "keywords": ["balanced", "medium pacing", "strong", "smooth"],
    },
    {
        "voice_id": "Aoede",
        "name": "Aoede",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Aoede.mp3",
        "keywords": ["clear", "slow pacing", "natural", "steady"],
    },
    {
        "voice_id": "Orus",
        "name": "Orus",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Orus.mp3",
        "keywords": ["balanced", "fast pacing", "gentle", "expressive"],
    },
    {
        "voice_id": "Leda",
        "name": "Leda",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Leda.mp3",
        "keywords": [
            "soft-bright",
            "high-pitched",
            "slow pacing",
            "gentle",
            "expressive",
        ],
    },
    {
        "voice_id": "Achernar",
        "name": "Achernar",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Achernar.mp3",
        "keywords": ["balanced", "fast pacing", "natural", "steady"],
    },
    {
        "voice_id": "Achird",
        "name": "Achird",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Achird.mp3",
        "keywords": ["clear", "fast pacing", "natural", "steady"],
    },
    {
        "voice_id": "Algenib",
        "name": "Algenib",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Algenib.mp3",
        "keywords": [
            "clear",
            "low-pitched",
            "medium pacing",
            "gentle",
            "smooth",
        ],
    },
    {
        "voice_id": "Algieba",
        "name": "Algieba",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Algieba.mp3",
        "keywords": [
            "clear",
            "low-pitched",
            "medium pacing",
            "strong",
            "expressive",
        ],
    },
    {
        "voice_id": "Alnilam",
        "name": "Alnilam",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Alnilam.mp3",
        "keywords": ["deep", "warm", "fast pacing", "natural", "smooth"],
    },
    {
        "voice_id": "Autonoe",
        "name": "Autonoe",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Autonoe.mp3",
        "keywords": ["balanced", "slow pacing", "natural", "smooth"],
    },
    {
        "voice_id": "Callirrhoe",
        "name": "Callirrhoe",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Callirrhoe.mp3",
        "keywords": ["balanced", "medium pacing", "natural", "steady"],
    },
    {
        "voice_id": "Despina",
        "name": "Despina",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Despina.mp3",
        "keywords": [
            "soft-bright",
            "high-pitched",
            "medium pacing",
            "strong",
            "steady",
        ],
    },
    {
        "voice_id": "Enceladus",
        "name": "Enceladus",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Enceladus.mp3",
        "keywords": ["balanced", "medium pacing", "natural", "smooth"],
    },
    {
        "voice_id": "Erinome",
        "name": "Erinome",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Erinome.mp3",
        "keywords": ["balanced", "medium pacing", "strong", "expressive"],
    },
    {
        "voice_id": "Gacrux",
        "name": "Gacrux",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Gacrux.mp3",
        "keywords": ["soft", "slow pacing", "strong", "smooth"],
    },
    {
        "voice_id": "Iapetus",
        "name": "Iapetus",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Iapetus.mp3",
        "keywords": ["deep", "warm", "medium pacing", "gentle", "steady"],
    },
    {
        "voice_id": "Laomedeia",
        "name": "Laomedeia",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Laomedeia.mp3",
        "keywords": ["soft", "medium pacing", "natural", "smooth"],
    },
    {
        "voice_id": "Pulcherrima",
        "name": "Pulcherrima",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Pulcherrima.mp3",
        "keywords": ["balanced", "fast pacing", "strong", "smooth"],
    },
    {
        "voice_id": "Rasalgethi",
        "name": "Rasalgethi",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Rasalgethi.mp3",
        "keywords": ["balanced", "medium pacing", "natural", "smooth"],
    },
    {
        "voice_id": "Sadachbia",
        "name": "Sadachbia",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Sadachbia.mp3",
        "keywords": ["balanced", "fast pacing", "natural", "expressive"],
    },
    {
        "voice_id": "Sadaltager",
        "name": "Sadaltager",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Sadaltager.mp3",
        "keywords": ["balanced", "slow pacing", "gentle", "smooth"],
    },
    {
        "voice_id": "Schedar",
        "name": "Schedar",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Schedar.mp3",
        "keywords": ["clear", "fast pacing", "natural", "steady"],
    },
    {
        "voice_id": "Sulafat",
        "name": "Sulafat",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Sulafat.mp3",
        "keywords": [
            "bright",
            "high-pitched",
            "slow pacing",
            "strong",
            "smooth",
        ],
    },
    {
        "voice_id": "Umbriel",
        "name": "Umbriel",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Umbriel.mp3",
        "keywords": ["balanced", "medium pacing", "gentle", "expressive"],
    },
    {
        "voice_id": "Vindemiatrix",
        "name": "Vindemiatrix",
        "gender": "female",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Vindemiatrix.mp3",
        "keywords": ["balanced", "medium pacing", "natural", "expressive"],
    },
    {
        "voice_id": "Zubenelgenubi",
        "name": "Zubenelgenubi",
        "gender": "male",
        "provider": TTS_PROVIDER_GEMINI,
        "source": "preset",
        "category": "prebuilt",
        "preview_url": f"{_GCS_VOICE_PREVIEW_BASE}/Zubenelgenubi.mp3",
        "keywords": ["soft", "slow pacing", "gentle", "smooth"],
    },
]

# Gemini TTS 音色按使用场景的推荐 shortlist（基于官方样本听感整理）
USE_CASES_SHORTLIST: Dict[str, List[str]] = {
    "general_ai_assistant": ["Callirrhoe", "Rasalgethi", "Enceladus"],
    "customer_support_help_center": ["Puck", "Achird", "Aoede"],
    "long_form_narration_explainers": [
        "Autonoe",
        "Sadaltager",
        "Zubenelgenubi",
    ],
    "calm_soothing_wellness": ["Zubenelgenubi", "Iapetus", "Laomedeia"],
    "premium_authoritative_executive": ["Algieba", "Fenrir", "Pulcherrima"],
    "energetic_marketing_promos": ["Schedar", "Sadachbia", "Orus"],
    "emotional_storytelling": ["Leda", "Erinome", "Vindemiatrix"],
    "bright_youthful_lively": ["Kore", "Sulafat", "Despina"],
}

# 预计算 Gemini 音色名称集合，用于快速查找
_GEMINI_VOICE_NAMES: Set[str] = {v["voice_id"] for v in GEMINI_PREBUILT_VOICES}


def parse_voice_id(voice_id: str) -> Tuple[str, str]:
    """
    解析 voice_id 为 (prefix, raw)。
    仅按第一个 '/' 分割；无 '/' 则 prefix 为空字符串（兼容旧数据）。
    例：parse_voice_id("google/Zephyr") -> ("google", "Zephyr")；parse_voice_id("Zephyr") -> ("", "Zephyr")。
    """
    if not voice_id:
        return ("", "")
    if "/" not in voice_id:
        return ("", voice_id)
    parts = voice_id.split("/", 1)
    return (parts[0], parts[1])


def is_gemini_voice(voice_id: Optional[str]) -> bool:
    """判断给定的 voice_id 是否为 Gemini TTS 预置音色（支持 provider 前缀与无前缀兼容）"""
    if not voice_id:
        return False
    prefix, raw = parse_voice_id(voice_id)
    if prefix == VOICE_ID_PREFIX_GEMINI:
        return True
    if prefix == VOICE_ID_PREFIX_ELEVENLABS:
        return False
    # 无前缀：兼容旧 DB/配置，按 raw 是否在预置集合
    return raw in _GEMINI_VOICE_NAMES


def get_gemini_voices() -> List[Dict[str, Any]]:
    """获取 Gemini TTS 预置音色列表（返回副本，voice_id 带 google/ 前缀）"""
    result = [v.copy() for v in GEMINI_PREBUILT_VOICES]
    for voice in result:
        voice["voice_id"] = f"{VOICE_ID_PREFIX_GEMINI}/{voice['voice_id']}"
    return result


def resolve_voice_message_narration_mode(
    raw_mode: Any,
) -> VoiceMessageNarrationMode:
    if isinstance(raw_mode, VoiceMessageNarrationMode):
        return raw_mode
    if isinstance(raw_mode, str):
        try:
            return VoiceMessageNarrationMode(raw_mode)
        except ValueError:
            logger.warning(
                "Unknown voice message narration mode: {}; fallback to {}",
                raw_mode,
                VoiceMessageNarrationMode.DIALOGUE_ONLY,
            )
    return VoiceMessageNarrationMode.DIALOGUE_ONLY


def select_default_gemini_voice_for_imate_gender(
    agent_gender: Optional[str],
) -> str:
    """
    选择 Gemini 源音色（用于 Gemini->ElevenLabs 变声链路）。
    未知性别或空值回退到 DEFAULT_GEMINI_TTS_VOICE_NAME。
    """
    if not agent_gender:
        return DEFAULT_GEMINI_TTS_VOICE_NAME
    normalized = agent_gender.strip().upper()
    return IMATE_GENDER_TO_DEFAULT_GEMINI_SOURCE_VOICE.get(
        normalized, DEFAULT_GEMINI_TTS_VOICE_NAME
    )


# 语速：1.0 = 正常；<1 减慢，>1 加快。与 Cloud TTS 文档一致。
# https://docs.cloud.google.com/text-to-speech/docs/gemini-tts
SPEAKING_RATE_MIN = 0.5
SPEAKING_RATE_MAX = 2.0
SPEAKING_RATE_DEFAULT = 1.0


@dataclass(frozen=True)
class TTSRequest:
    text: str
    voice_id: str
    model_id: str
    output_format: str
    language_code: Optional[str] = None
    stability: float = DEFAULT_STABILITY
    similarity_boost: float = DEFAULT_SIMILARITY_BOOST
    # 语速倍数，仅 Gemini TTS 通过 prompt 生效；1.0=正常，0.5~2.0 有效范围；与 SPEAKING_RATE_DEFAULT 一致以免默认请求误加 pace 指令
    speaking_rate: float = SPEAKING_RATE_DEFAULT
    voice_message_narration_mode: VoiceMessageNarrationMode = (
        VoiceMessageNarrationMode.DIALOGUE_ONLY
    )


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


# 公开接口，供 live chat 等将 PCM 转为 WAV 时复用
pcm_to_wav = _pcm_to_wav


def _looks_like_gemini_voice_name(voice_id: str) -> bool:
    """
    仅在 voice_id 没有 provider/ 前缀时由调用方使用；用于无前缀且看起来像 Gemini 名的兼容。
    有前缀时直接 return False（不应依赖此启发式）。
    """
    if not voice_id:
        return False
    prefix, raw = parse_voice_id(voice_id)
    if prefix != "":
        return False
    if raw in _GEMINI_VOICE_NAMES:
        return True
    return raw.isalpha() and 2 <= len(raw) <= 32


@traceable(
    name="generate_gemini_tts",
    run_type="chain",
)
def _generate_gemini_tts(
    client: Any,
    model: str,
    contents: List[Any],
    config: Any,
) -> Tuple[bytes, Optional[str]]:
    """
    调用 Gemini TTS 非流式接口，返回 (raw_bytes, mime_type)。
    供 GeminiTTSAPI.synthesize 与 synthesize_with_roleplay_prompt 使用。
    """
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    if (
        response.candidates is None
        or not response.candidates
        or response.candidates[0].content is None
        or response.candidates[0].content.parts is None
        or not response.candidates[0].content.parts
    ):
        return b"", None
    part0 = response.candidates[0].content.parts[0]
    inline = getattr(part0, "inline_data", None)
    if not inline or not getattr(inline, "data", None):
        return b"", None
    mt = getattr(inline, "mime_type", None)
    return inline.data, mt


def _pace_instruction_for_gemini(speaking_rate: float) -> str:
    """
    根据 speaking_rate 生成 Gemini TTS 的语速说明（自然语言 prompt）。
    文档：Enhanced pace and pronunciation control；Values <1 减慢，>1 加快，默认 1。
    """
    if speaking_rate <= 0 or speaking_rate == SPEAKING_RATE_DEFAULT:
        return ""
    rate = max(SPEAKING_RATE_MIN, min(SPEAKING_RATE_MAX, speaking_rate))
    if rate == SPEAKING_RATE_DEFAULT:
        return ""
    if rate < 1.0:
        return f"Deliver the following at {rate:.1f}x normal speaking rate (slower). "
    return (
        f"Deliver the following at {rate:.1f}x normal speaking rate (faster). "
    )


def sanitize_text_for_gemini_tts(text: str) -> Tuple[List[str], List[str]]:
    """
    将文本按括号拆成舞台说明与台词：每个 "(...)" 内为 stage_direction，括号外为 dialogue 片段。
    返回 (stage_directions, dialogue) 两个列表，供 roleplay prompt 分别传给模型。
    """
    stage_directions = []
    dialogue = []
    for part in text.split("("):
        if ")" in part:
            stage_directions.append(part.split(")", 1)[0])
            dialogue.append(part.split(")", 1)[1])
        else:
            dialogue.append(part)
    return stage_directions, dialogue


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
        self._client: Optional[Any] = None

    def _get_client(self) -> Optional[Any]:
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

            gemini_live_config = (
                global_config_loaded_from_config_yaml.gemini_live
            )
            self._client = get_kernel_gemini_client(
                GeminiClientOptions(
                    vertexai=True,
                    project=gemini_live_config.project_id,
                    location=gemini_live_config.location,
                    wrap_langsmith=True,
                    tags=("google-genai", "gemini-tts", "app-core-voice"),
                    metadata={
                        "source": "app.core.voice.tts_api",
                        "project_id": gemini_live_config.project_id,
                        "location": gemini_live_config.location,
                    },
                    chat_name="Inty_GeminiTTS",
                    credentials_path=gcp_key_path,
                )
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
            logger.info(
                "Gemini TTS 未配置可用凭据，跳过并回退到其它 TTS provider"
            )
            return None

        prefix, raw = parse_voice_id(request.voice_id)
        if prefix == VOICE_ID_PREFIX_GEMINI:
            voice_name = raw
        elif prefix == "":
            voice_name = (
                request.voice_id
                if _looks_like_gemini_voice_name(request.voice_id)
                else self._default_voice_name
            )
        else:
            logger.error(f"Unknown voice_id: {request.voice_id}")
            voice_name = self._default_voice_name

        user_text = request.text
        pace = _pace_instruction_for_gemini(request.speaking_rate)
        if pace:
            user_text = pace + user_text
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_text)],
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

        model_to_use = request.model_id or self._model
        try:
            # 非流式调用放到线程池避免阻塞 event loop
            audio_bytes, mime_type = await asyncio.to_thread(
                _generate_gemini_tts, client, model_to_use, contents, config
            )

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

    @traceable
    async def synthesize_with_roleplay_prompt(
        self, request: TTSRequest
    ) -> Optional[TTSResult]:
        """
        Same as synthesize() but sends TTS_ROLEPLAY_INSTRUCTION + request.text
        so the model acts as a voice actor: parentheticals are stage directions
        (do not speak them; use them to inform delivery). No text cleaning
        should be applied to request.text by the caller.
        """
        if not (request.text or "").strip():
            logger.warning("synthesize_with_roleplay_prompt: 文本为空，跳过")
            return None

        client = self._get_client()
        if client is None:
            logger.info(
                "Gemini TTS 未配置可用凭据，跳过并回退到其它 TTS provider"
            )
            return None

        prefix, raw = parse_voice_id(request.voice_id)
        if prefix == VOICE_ID_PREFIX_GEMINI:
            voice_name = raw
        elif prefix == "":
            voice_name = (
                request.voice_id
                if _looks_like_gemini_voice_name(request.voice_id)
                else self._default_voice_name
            )
        else:
            voice_name = self._default_voice_name

        # TTS 模型不支持 system_instruction（流式/非流式均 400），将角色说明放入 user 内容
        pace = _pace_instruction_for_gemini(request.speaking_rate)
        narration_mode = resolve_voice_message_narration_mode(
            request.voice_message_narration_mode
        )
        if (
            narration_mode
            == VoiceMessageNarrationMode.DIALOGUE_AND_STAGE_DIRECTIONS
        ):
            full_text = request.text
            if pace:
                full_text = pace + full_text
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=TTS_FULL_NARRATION_INSTRUCTION
                        )
                    ],
                ),
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=full_text)],
                ),
            ]
        else:
            stage_directions, dialogues = sanitize_text_for_gemini_tts(
                request.text
            )
            dialogue_text = (
                "Do not speak the stage directions, only speak the dialogues: "
                + " ".join(dialogues)
            )
            if pace:
                dialogue_text = pace + dialogue_text
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=TTS_ROLEPLAY_INSTRUCTION)],
                ),
            ]
            if stage_directions:
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(
                                text="Stage directions to describe the scene: "
                                + "\n".join(stage_directions)
                            )
                        ],
                    )
                )
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=dialogue_text)],
                )
            )

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

        model_to_use = request.model_id or self._model
        try:
            audio_bytes, mime_type = await asyncio.to_thread(
                _generate_gemini_tts, client, model_to_use, contents, config
            )

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

    @traceable
    async def synthesize_with_full_dialogue_prompt(
        self, request: TTSRequest
    ) -> Optional[TTSResult]:
        """
        Full-dialogue Gemini TTS:
        - sends role instruction + original text
        - does not split stage directions and dialogues
        """
        if not (request.text or "").strip():
            logger.warning(
                "synthesize_with_full_dialogue_prompt: 文本为空，跳过"
            )
            return None

        client = self._get_client()
        if client is None:
            logger.info(
                "Gemini TTS 未配置可用凭据，跳过并回退到其它 TTS provider"
            )
            return None

        prefix, raw = parse_voice_id(request.voice_id)
        if prefix == VOICE_ID_PREFIX_GEMINI:
            voice_name = raw
        elif prefix == "":
            voice_name = (
                request.voice_id
                if _looks_like_gemini_voice_name(request.voice_id)
                else self._default_voice_name
            )
        else:
            voice_name = self._default_voice_name

        pace = _pace_instruction_for_gemini(request.speaking_rate)
        full_dialogue_text = request.text
        if pace:
            full_dialogue_text = pace + full_dialogue_text

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=TTS_FULL_DIALOGUE_CONVERSION_INSTRUCTION
                    )
                ],
            ),
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=full_dialogue_text)],
            ),
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

        model_to_use = request.model_id or self._model
        try:
            audio_bytes, mime_type = await asyncio.to_thread(
                _generate_gemini_tts, client, model_to_use, contents, config
            )

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
            prefix, raw = parse_voice_id(request.voice_id)
            elevenlabs_voice_id = (
                raw
                if prefix == VOICE_ID_PREFIX_ELEVENLABS
                else request.voice_id
            )

            voice_settings = VoiceSettings(
                stability=request.stability,
                similarity_boost=request.similarity_boost,
            )

            kwargs: Dict[str, Any] = {
                "text": request.text,
                "voice_id": elevenlabs_voice_id,
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

    @staticmethod
    def _mime_type_from_output_format(output_format: str) -> str:
        normalized = (output_format or "").lower()
        if normalized.startswith("mp3_"):
            return "audio/mpeg"
        if normalized.startswith("pcm_"):
            return "audio/pcm"
        if normalized.startswith("ulaw_"):
            return "audio/basic"
        if normalized.startswith("alaw_"):
            return "audio/basic"
        if normalized.startswith("opus_"):
            return "audio/ogg"
        return "application/octet-stream"

    async def convert_with_voice_changer(
        self,
        *,
        source_audio_bytes: bytes,
        source_mime_type: str,
        target_voice_id: str,
        model_id: str,
        output_format: str,
    ) -> Optional[TTSResult]:
        """
        ElevenLabs speech-to-speech voice changer。
        """
        if not source_audio_bytes:
            logger.warning("ElevenLabs voice changer 输入音频为空")
            return None

        prefix, raw = parse_voice_id(target_voice_id)
        elevenlabs_voice_id = (
            raw if prefix == VOICE_ID_PREFIX_ELEVENLABS else target_voice_id
        )
        filename = (
            "source.wav"
            if "wav" in (source_mime_type or "").lower()
            else "source.mp3"
        )
        content_type = source_mime_type or "application/octet-stream"
        audio_payload = (filename, source_audio_bytes, content_type)

        try:
            audio_chunks = await asyncio.to_thread(
                lambda: list(
                    self._client.speech_to_speech.convert(
                        voice_id=elevenlabs_voice_id,
                        audio=audio_payload,
                        model_id=model_id,
                        output_format=output_format,
                    )
                )
            )
            converted_audio = b"".join(audio_chunks)
            if not converted_audio:
                logger.error("ElevenLabs voice changer 返回空音频数据")
                return None
            return TTSResult(
                audio_bytes=converted_audio,
                mime_type=self._mime_type_from_output_format(output_format),
            )
        except Exception as e:
            logger.error(f"ElevenLabs voice changer 调用失败: {str(e)}")
            logger.exception("ElevenLabs voice changer 异常详细信息:")
            return None

    async def get_all_voices(self, *, show_legacy: bool = True) -> Any:
        return await asyncio.to_thread(
            self._client.voices.get_all, show_legacy=show_legacy
        )

    async def get_shared_voices(self, **search_params: Any) -> Any:
        return await asyncio.to_thread(
            self._client.voices.get_shared, **search_params
        )

    async def get_voice(self, voice_id: str) -> Any:
        return await asyncio.to_thread(self._client.voices.get, voice_id)
