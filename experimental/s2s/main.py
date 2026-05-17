from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

OPENAI_API_KEY_PLACEHOLDER = "YOUR_OPENAI_API_KEY_HERE"


@dataclass(frozen=True)
class LiveVoiceSettings:
    api_key: str
    model: str
    voice: str
    instructions: str


def load_settings() -> LiveVoiceSettings:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == OPENAI_API_KEY_PLACEHOLDER:
        raise ValueError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and fill a real key."
        )

    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
    voice = os.getenv("OPENAI_REALTIME_VOICE", "alloy")
    instructions = os.getenv(
        "OPENAI_REALTIME_INSTRUCTIONS",
        "You are a concise, friendly voice assistant in a live phone call.",
    )
    return LiveVoiceSettings(
        api_key=api_key,
        model=model,
        voice=voice,
        instructions=instructions,
    )


async def run_realtime_voice_call(settings: LiveVoiceSettings) -> None:
    # Implementation follows OpenAI realtime push-to-talk streaming pattern:
    # 1) send microphone PCM chunks to input_audio_buffer
    # 2) receive response.audio.delta chunks and play in near real-time.
    import sounddevice as sd
    from openai import AsyncOpenAI

    from audio_util import AudioPlayerAsync, CHANNELS, SAMPLE_RATE

    client = AsyncOpenAI(api_key=settings.api_key)
    audio_player = AudioPlayerAsync()
    connection_ready = asyncio.Event()
    connection: Any | None = None
    last_audio_item_id: str | None = None

    async def handle_realtime_events() -> None:
        nonlocal connection, last_audio_item_id
        async with client.beta.realtime.connect(model=settings.model) as conn:
            connection = conn
            connection_ready.set()
            print(f"Connected to realtime model: {settings.model}")

            await conn.session.update(
                session={
                    "turn_detection": {"type": "server_vad"},
                    "voice": settings.voice,
                    "instructions": settings.instructions,
                    "modalities": ["audio", "text"],
                }
            )

            transcript_by_item: dict[str, str] = {}
            async for event in conn:
                if event.type == "session.created":
                    print(f"Session created: {event.session.id}")
                    continue

                if event.type == "response.audio.delta":
                    if event.item_id != last_audio_item_id:
                        audio_player.reset_frame_count()
                        last_audio_item_id = event.item_id
                    audio_player.add_data(base64.b64decode(event.delta))
                    continue

                if event.type == "response.audio_transcript.delta":
                    transcript_by_item[event.item_id] = (
                        transcript_by_item.get(event.item_id, "") + event.delta
                    )
                    print(
                        f"\rAI: {transcript_by_item[event.item_id]}",
                        end="",
                        flush=True,
                    )
                    continue

                if event.type == "response.done":
                    print()
                    continue

    async def stream_microphone_audio() -> None:
        nonlocal connection
        read_size = int(SAMPLE_RATE * 0.02)
        stream = sd.InputStream(
            channels=CHANNELS,
            samplerate=SAMPLE_RATE,
            dtype="int16",
        )
        stream.start()
        print("Microphone stream started. Speak naturally. Ctrl+C to stop.")

        await connection_ready.wait()
        try:
            while True:
                if stream.read_available < read_size:
                    await asyncio.sleep(0)
                    continue

                data, _ = stream.read(read_size)
                if connection is not None:
                    await connection.input_audio_buffer.append(
                        audio=base64.b64encode(data).decode("utf-8")
                    )
                await asyncio.sleep(0)
        finally:
            stream.stop()
            stream.close()

    realtime_task = asyncio.create_task(handle_realtime_events())
    mic_task = asyncio.create_task(stream_microphone_audio())
    try:
        await asyncio.gather(realtime_task, mic_task)
    finally:
        audio_player.stop()
        audio_player.terminate()


def main() -> None:
    from openai import APIConnectionError, APIStatusError, AuthenticationError

    try:
        settings = load_settings()
    except ValueError as error:
        print(error)
        raise SystemExit(2) from error

    print("Starting GPT live voice demo...")
    print(f"Model: {settings.model}")
    print(f"Voice: {settings.voice}")
    try:
        asyncio.run(run_realtime_voice_call(settings))
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except AuthenticationError as error:
        print(f"Authentication failed: {error}")
        raise
    except APIConnectionError as error:
        print(f"Network error while connecting realtime API: {error}")
        raise
    except APIStatusError as error:
        print(
            f"Realtime API request failed: status={error.status_code}, body={error}"
        )
        raise


if __name__ == "__main__":
    main()
