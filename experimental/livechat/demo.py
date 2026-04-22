import asyncio
import json
import os
from pathlib import Path

import websockets
from google import genai
from google.genai import types

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SA_KEY = _REPO_ROOT / "inty-backend-key.json"
os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(_DEFAULT_SA_KEY),
)

_CREDENTIALS_PATH = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
with _CREDENTIALS_PATH.open(encoding="utf-8") as f:
    _VERTEX_PROJECT = json.load(f)["project_id"]

client = genai.Client(
    vertexai=True,
    project=_VERTEX_PROJECT,
    location="us-central1",
)

MODEL = "gemini-live-2.5-flash-native-audio"


# def resumable_session_example():
#     pass


# if __name__ == "__main__":
#     resumable_session_example()


def build_live_config() -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
            ),
            language_code="en-US",
        ),
        session_resumption=types.SessionResumptionConfig(
            handle=session_handle,
        ),
    )


async def resumable_session_example():
    session_handle = None

    print("Starting a new session...")

    try:
        async with client.aio.live.connect(
            model=MODEL,
            config=types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                session_resumption=types.SessionResumptionConfig(
                    handle=session_handle,
                ),
            ),
        ) as session:
            await session.send_client_content(
                turns=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text="Hello!")],
                    )
                ],
                turn_complete=True,
            )
            async for message in session.receive():
                if message.session_resumption_update:
                    update = message.session_resumption_update
                    if update.resumable and update.new_handle:
                        session_handle = update.new_handle
                        print(f"Received session handle: {session_handle}")
                        break
                if message.server_content and message.server_content.turn_complete:
                    print(
                        f"Received server content: {message.server_content},text:{message.text}"
                    )
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket exception: {e}")
        return

    if not session_handle:
        print("Did not receive a session handle. Cannot demonstrate resumption.")
        return

    print(f"\nSimulating disconnect and reconnecting with handle {session_handle}...")

    try:
        async with client.aio.live.connect(
            model=MODEL,
            config=types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                session_resumption=types.SessionResumptionConfig(
                    handle=session_handle,
                ),
            ),
        ) as session:
            print("Successfully resumed session.")
            await session.send_client_content(
                turns=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text="I am back!")],
                    )
                ],
                turn_complete=True,
            )
            async for message in session.receive():
                if message.session_resumption_update:
                    update = message.session_resumption_update
                    if update.resumable and update.new_handle:
                        session_handle = update.new_handle
                        print(f"Received updated session handle: {session_handle}")
                if message.server_content:
                    print(f"Received server content: {message.server_content}")
                    if message.server_content.turn_complete:
                        break
            print("Resumed session finished.")

    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket exception: {e}")
        return


if __name__ == "__main__":
    asyncio.run(resumable_session_example())
