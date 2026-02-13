"""
Voice list API: Gemini (and later ElevenLabs) voice names and metadata as Pydantic models.
Delegates to app.core.voice.tts_api for underlying data; no dict in public API.
"""

from __future__ import annotations

from app.core.voice.tts_api import get_gemini_voices
from pydantic import BaseModel


class VoiceMetadata(BaseModel):
    """
    Metadata for a TTS voice (Gemini or ElevenLabs).
    Single representation for both providers; ElevenLabs to be wired in later.
    """

    voice_id: str
    name: str
    gender: str
    provider: str
    source: str
    category: str
    preview_url: str
    keywords: list[str]


def list_gemini_voices() -> list[VoiceMetadata]:
    """
    Return Gemini TTS prebuilt voices (names + metadata) as Pydantic models.
    Delegates to app.core.voice.tts_api.get_gemini_voices() for the underlying data.
    """
    raw = get_gemini_voices()
    return [VoiceMetadata.model_validate(d) for d in raw]
