"""Fake text-to-speech providers used by the test backend environment."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from app.core.voice.tts_api import TTSRequest, TTSResult


def _silent_wav_bytes(
    duration_seconds: float = 0.1, sample_rate: int = 24000
) -> bytes:
    frame_count = max(1, int(duration_seconds * sample_rate))
    pcm = b"\x00\x00" * frame_count
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buf.getvalue()


@dataclass(frozen=True)
class _FakeVoice:
    voice_id: str
    name: str
    category: str = "premade"
    is_owner: bool = False

    def model_dump(self) -> dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "category": self.category,
            "is_owner": self.is_owner,
        }


class FakeTextToSpeechAPI:
    """Deterministic local TTS implementation with the same async surface as providers."""

    def __init__(self) -> None:
        self._audio = _silent_wav_bytes()
        self._voices = [
            _FakeVoice(
                voice_id="fake-elevenlabs-voice",
                name="Fake ElevenLabs Voice",
            )
        ]

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        return TTSResult(audio_bytes=self._audio, mime_type="audio/wav")

    async def synthesize_with_roleplay_prompt(
        self, request: TTSRequest
    ) -> TTSResult:
        return TTSResult(audio_bytes=self._audio, mime_type="audio/wav")

    async def synthesize_with_full_dialogue_prompt(
        self, request: TTSRequest
    ) -> TTSResult:
        return TTSResult(audio_bytes=self._audio, mime_type="audio/wav")

    async def convert_with_voice_changer(
        self,
        *,
        source_audio_bytes: bytes,
        source_mime_type: str,
        target_voice_id: str,
        model_id: str,
        output_format: str,
    ) -> TTSResult:
        return TTSResult(audio_bytes=self._audio, mime_type="audio/wav")

    async def get_all_voices(self, *, show_legacy: bool = True) -> Any:
        return SimpleNamespace(voices=list(self._voices))

    async def get_shared_voices(self, **kwargs: Any) -> Any:
        return SimpleNamespace(voices=[])

    async def get_voice(self, voice_id: str) -> _FakeVoice:
        for voice in self._voices:
            if voice.voice_id == voice_id:
                return voice
        raise ValueError(f"Fake voice not found: {voice_id}")
