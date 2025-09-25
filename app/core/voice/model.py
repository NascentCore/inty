"""
语音模型配置与设置：
1. 配置指模型实体和根本性特征，模型本身决定了语音生成的真实、多变、和其他底层能力
   这种底层能力与角色匹配
2. 设置指可以临时调整的生成参数，用于微调声音效果；如速度、稳定度、等
   这些设置的微调用于一个人在不同场景下语音的生成
"""
from enum import StrEnum


class Provider(StrEnum):
    # https://cloud.google.com/text-to-speech
    Google = "google"
    # https://elevenlabs.io/docs/api-reference/text-to-speech
    ElevenLabs = "eleven"
    # 以下是待调研的服务商
    # http://hume.ai/
    HUMEAI = "humeai"
    # https://fal.ai/
    FALAI = "falai"


class ElevenLabsModels(StrEnum):
    """
    ElevenLabs 模型列表
    """
    V3 = "elevenlabs_v3"
    FLASH_V2_5 = "elevenlabs_flash_v2_5"


class Config:
    """
    语音模型设置，包括模型名称与音色选择等全局设定。
    语音模型名称采用与 openrouter 一致的命名格式 <provider>/<provider-specific-model-name>
    """
    provider: Provider = Provider.ElevenLabs
    model: str = ElevenLabsModels.V3
    # 在供应商服务内的 ID，如 elevenlabs 的 voice_id，
    voice_id: str


class ElevenLabsVoiceSettings:
    """
    ElevenLabs 模型支持的语音设置

    语音设置有别于模型设置，是可以用于所有生成场景的通用参数。
    也就是切换模型、音色，都可以适用下面的语音设置。
    """
    voice_id: str
    output_format: str
    stability: float
    similarity_boost: float
