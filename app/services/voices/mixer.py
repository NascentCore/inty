"""
与调度多个语音 AI 服务相关的代码
包含音色映射和提供商选择逻辑
"""

# CREATED_BY_AGENT

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VoiceProvider(str, Enum):
    GEMINI = "gemini"
    ELEVENLABS = "elevenlabs"


@dataclass
class VoiceSelection:
    requested_voice_id: Optional[str]
    gemini_voice_name: Optional[str]
    elevenlabs_voice_id: Optional[str]

    def provider_voice_id(self, provider: VoiceProvider) -> Optional[str]:
        if provider == VoiceProvider.GEMINI:
            voice_name = (self.gemini_voice_name or "").strip()
            if not voice_name:
                return None
            return f"gemini:{voice_name.lower()}"
        return self.elevenlabs_voice_id


# 性别到音色ID的映射
GENDER_VOICE_MAPPING = {
    "MALE": "rHWSYoq8UlV0YIBKMryp",
    "FEMALE": "4tRn1lSkEn13EVTuqb0g",
    "OTHER": "O7p2vmz2iEYgMXxkbsif",
}

GEMINI_GENDER_DEFAULT_MAPPING = {
    "MALE": "Charon",
    "FEMALE": "Kore",
    "OTHER": "Zephyr",
}

GEMINI_TO_ELEVEN_VOICE_ID = {
    "kore": "4tRn1lSkEn13EVTuqb0g",
    "charon": "rHWSYoq8UlV0YIBKMryp",
    "zephyr": "O7p2vmz2iEYgMXxkbsif",
}

ELEVEN_TO_GEMINI_VOICE_ID = {value: key for key, value in GEMINI_TO_ELEVEN_VOICE_ID.items()}
