"""
TTS 模型目录（provider-aware）。

关键步骤总结（AI 工作记录）：
1) 先把 Gemini / ElevenLabs 的可用 TTS 模型定义为结构化目录，避免字符串散落在业务逻辑里。
2) 提供按 model id / nickname 的 resolver 与 must_resolve 变体，统一 Fail Loud 行为。
3) 提供 provider 归属判断与 allowlist，供 VoiceService 做请求级一致性校验。
"""

from dataclasses import dataclass
from typing import Optional

from app.core.voice.tts_api import TTS_PROVIDER_ELEVENLABS, TTS_PROVIDER_GEMINI

TTS_MODEL_STATUS_ACTIVE = "active"
TTS_MODEL_STATUS_DEPRECATED = "deprecated"


@dataclass(frozen=True)
class TTSModelCapabilities:
    supports_language_code: bool
    supports_prompted_roleplay: bool


@dataclass(frozen=True)
class TTSModelSpec:
    provider: str
    id_on_provider: str
    nickname: str
    capabilities: TTSModelCapabilities
    status: str = TTS_MODEL_STATUS_ACTIVE


GEMINI_2_5_FLASH_TTS = TTSModelSpec(
    provider=TTS_PROVIDER_GEMINI,
    id_on_provider="gemini-2.5-flash-tts",
    nickname="Gemini 2.5 Flash TTS",
    capabilities=TTSModelCapabilities(
        supports_language_code=False,
        supports_prompted_roleplay=True,
    ),
)

GEMINI_2_5_PRO_TTS = TTSModelSpec(
    provider=TTS_PROVIDER_GEMINI,
    id_on_provider="gemini-2.5-pro-tts",
    nickname="Gemini 2.5 Pro TTS",
    capabilities=TTSModelCapabilities(
        supports_language_code=False,
        supports_prompted_roleplay=True,
    ),
)

ELEVEN_MULTILINGUAL_V2 = TTSModelSpec(
    provider=TTS_PROVIDER_ELEVENLABS,
    id_on_provider="eleven_multilingual_v2",
    nickname="Eleven Multilingual v2",
    capabilities=TTSModelCapabilities(
        supports_language_code=False,
        supports_prompted_roleplay=False,
    ),
)

ELEVEN_FLASH_V2_5 = TTSModelSpec(
    provider=TTS_PROVIDER_ELEVENLABS,
    id_on_provider="eleven_flash_v2_5",
    nickname="Eleven Flash v2.5",
    capabilities=TTSModelCapabilities(
        supports_language_code=False,
        supports_prompted_roleplay=False,
    ),
)

ELEVEN_TURBO_V2_5 = TTSModelSpec(
    provider=TTS_PROVIDER_ELEVENLABS,
    id_on_provider="eleven_turbo_v2_5",
    nickname="Eleven Turbo v2.5",
    capabilities=TTSModelCapabilities(
        supports_language_code=True,
        supports_prompted_roleplay=False,
    ),
)

TTS_MODELS = [
    GEMINI_2_5_FLASH_TTS,
    GEMINI_2_5_PRO_TTS,
    ELEVEN_MULTILINGUAL_V2,
    ELEVEN_FLASH_V2_5,
    ELEVEN_TURBO_V2_5,
]

# Gemini 聊天 TTS 允许的模型（配置项 free/sub_user_chat_tts_model 应落在此集合）
CHAT_TTS_GEMINI_MODEL_ALLOWLIST = [
    GEMINI_2_5_FLASH_TTS,
    GEMINI_2_5_PRO_TTS,
]

# ElevenLabs 默认 TTS 模型 allowlist（配置项 elevenlabs.model 应落在此集合）
ELEVENLABS_DEFAULT_MODEL_ALLOWLIST = [
    ELEVEN_MULTILINGUAL_V2,
    ELEVEN_FLASH_V2_5,
    ELEVEN_TURBO_V2_5,
]


def resolve_tts_model_by_id(model_id: str) -> Optional[TTSModelSpec]:
    normalized = model_id.strip()
    for model in TTS_MODELS:
        if model.id_on_provider == normalized:
            return model
    return None


def resolve_tts_model_by_nickname(nickname: str) -> Optional[TTSModelSpec]:
    normalized = nickname.strip()
    for model in TTS_MODELS:
        if model.nickname == normalized:
            return model
    return None


def must_resolve_tts_model_by_id(model_id: str) -> TTSModelSpec:
    model = resolve_tts_model_by_id(model_id)
    if model:
        return model
    allowed_model_ids = [item.id_on_provider for item in TTS_MODELS]
    raise ValueError(
        f"TTS model {model_id!r} not allowed; allowed model ids: {allowed_model_ids}"
    )


def must_resolve_tts_model_by_nickname(nickname: str) -> TTSModelSpec:
    model = resolve_tts_model_by_nickname(nickname)
    if model:
        return model
    allowed_nicknames = [item.nickname for item in TTS_MODELS]
    raise ValueError(
        f"TTS model nickname {nickname!r} not allowed; allowed nicknames: {allowed_nicknames}"
    )


def is_model_belongs_to_provider(model: str, provider: str) -> bool:
    model_spec = resolve_tts_model_by_id(model)
    if not model_spec:
        return False
    return model_spec.provider == provider
