"""Fake text-to-speech providers used by the test backend environment."""

from __future__ import annotations

import io
import wave

from app.core.voice.tts_api import TTSRequest, TTSResult


def _silent_wav_bytes(duration_seconds: float = 0.1, sample_rate: int = 24000) -> bytes:
    frame_count = max(1, int(duration_seconds * sample_rate))
    pcm = b"\x00\x00" * frame_count
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buf.getvalue()


class FakeTextToSpeechAPI:
    """Deterministic local TTS implementation with the same async surface as providers."""

    def __init__(self) -> None:
        self._audio = _silent_wav_bytes()

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        return TTSResult(audio_bytes=self._audio, mime_type="audio/wav")

    async def synthesize_with_roleplay_prompt(self, request: TTSRequest) -> TTSResult:
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
