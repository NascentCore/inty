from __future__ import annotations

import os
import wave
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_VOICE_NAME = "Kore"
GEMINI_DEMO_TEXT = (
    "Say cheerfully: Hello from Gemini TTS. I will now change my voice with "
    "ElevenLabs Voice Changer."
)

ELEVENLABS_MODEL_ID = "eleven_multilingual_sts_v2"
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_ELEVENLABS_TARGET_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"


@dataclass(frozen=True)
class GeminiAudio:
    pcm_data: bytes
    mime_type: str


@dataclass(frozen=True)
class OutputPaths:
    gemini_wav_path: Path
    voice_changed_audio_path: Path


def get_required_env_var(env_name: str) -> str:
    value = os.getenv(env_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {env_name}")
    return value


def get_sample_rate(mime_type: str) -> int:
    for token in mime_type.split(";"):
        cleaned = token.strip()
        if cleaned.lower().startswith("rate="):
            try:
                return int(cleaned.split("=", 1)[1])
            except ValueError:
                return 24000
    return 24000


def get_output_extension(output_format: str) -> str:
    codec = output_format.split("_", 1)[0].lower()
    if codec == "mp3":
        return ".mp3"
    if codec == "pcm":
        return ".wav"
    if codec == "opus":
        return ".opus"
    return ".audio"


def get_output_paths(base_directory: Path, output_format: str) -> OutputPaths:
    output_directory = base_directory / "outputs"
    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OutputPaths(
        gemini_wav_path=output_directory / f"gemini_tts_{timestamp}.wav",
        voice_changed_audio_path=output_directory
        / f"elevenlabs_voice_changed_{timestamp}{get_output_extension(output_format)}",
    )


def generate_gemini_audio(
    gemini_client: genai.Client,
    text: str,
    voice_name: str,
) -> GeminiAudio:
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        ),
    )

    if not response.candidates:
        raise RuntimeError("Gemini did not return any candidates.")
    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        raise RuntimeError("Gemini candidate does not contain content parts.")
    first_part = candidate.content.parts[0]
    if not first_part.inline_data or not first_part.inline_data.data:
        raise RuntimeError(
            "Gemini response does not contain inline audio data."
        )

    mime_type = first_part.inline_data.mime_type or "audio/L16;rate=24000"
    return GeminiAudio(
        pcm_data=first_part.inline_data.data,
        mime_type=mime_type,
    )


def save_pcm_as_wav(
    output_path: Path, pcm_data: bytes, sample_rate: int
) -> None:
    with wave.open(str(output_path), "wb") as wave_file:
        wave_file.setnchannels(1)
        wave_file.setsampwidth(2)
        wave_file.setframerate(sample_rate)
        wave_file.writeframes(pcm_data)


def run_elevenlabs_voice_changer(
    elevenlabs_client: ElevenLabs,
    source_audio_path: Path,
    target_voice_id: str,
    model_id: str,
    output_format: str,
) -> bytes:
    source_audio = BytesIO(source_audio_path.read_bytes())
    changed_audio_stream = elevenlabs_client.speech_to_speech.convert(
        voice_id=target_voice_id,
        audio=source_audio,
        model_id=model_id,
        output_format=output_format,
    )
    return b"".join(changed_audio_stream)


def main() -> None:
    # Flow summary:
    # 1) Gemini TTS generates PCM bytes.
    # 2) Save Gemini result to local WAV.
    # 3) Use ElevenLabs speech-to-speech to change voice and save output.
    load_dotenv()

    gemini_api_key = get_required_env_var("GEMINI_API_KEY")
    elevenlabs_api_key = get_required_env_var("ELEVENLABS_API_KEY")
    target_voice_id = os.getenv(
        "ELEVENLABS_TARGET_VOICE_ID",
        DEFAULT_ELEVENLABS_TARGET_VOICE_ID,
    )

    output_paths = get_output_paths(
        Path(__file__).resolve().parent, ELEVENLABS_OUTPUT_FORMAT
    )

    print("Step 1/2: generating audio with Gemini TTS ...")
    gemini_client = genai.Client(api_key=gemini_api_key)
    gemini_audio = generate_gemini_audio(
        gemini_client=gemini_client,
        text=GEMINI_DEMO_TEXT,
        voice_name=GEMINI_VOICE_NAME,
    )
    sample_rate = get_sample_rate(gemini_audio.mime_type)
    save_pcm_as_wav(
        output_path=output_paths.gemini_wav_path,
        pcm_data=gemini_audio.pcm_data,
        sample_rate=sample_rate,
    )
    print(f"Gemini audio saved to: {output_paths.gemini_wav_path}")

    print("Step 2/2: changing voice with ElevenLabs Voice Changer API ...")
    elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
    changed_audio = run_elevenlabs_voice_changer(
        elevenlabs_client=elevenlabs_client,
        source_audio_path=output_paths.gemini_wav_path,
        target_voice_id=target_voice_id,
        model_id=ELEVENLABS_MODEL_ID,
        output_format=ELEVENLABS_OUTPUT_FORMAT,
    )
    output_paths.voice_changed_audio_path.write_bytes(changed_audio)
    print(
        f"Voice-changed audio saved to: {output_paths.voice_changed_audio_path}"
    )


if __name__ == "__main__":
    main()
