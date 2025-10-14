"""
# Installation
# on linux
sudo apt-get install portaudio19-dev

# on mac
brew install portaudio

python3 -m venv env
source env/bin/activate
pip install google-genai
"""

import asyncio

import pyaudio
from google import genai
from google.genai import types

from app.utils.gemini import get_genai_client

CHUNK=4200
FORMAT=pyaudio.paInt16
CHANNELS=1
RECORD_SECONDS=5
MODEL = 'gemini-live-2.5-flash-preview-native-audio'
INPUT_RATE=16000
OUTPUT_RATE=24000

client = get_genai_client()
config = {
    "response_modalities": ["AUDIO"],
    "input_audio_transcription": {},  # Configure input transcription
    "output_audio_transcription": {},  # Configure output transcription
}

async def main():
    print(MODEL)
    p = pyaudio.PyAudio()
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        #exit()
        async def send():
            stream = p.open(
                format=FORMAT, channels=CHANNELS, rate=INPUT_RATE, input=True, frames_per_buffer=CHUNK)
            while True:
                frame = stream.read(CHUNK)
                await session.send(input={"data": frame, "mime_type": "audio/pcm"})
                await asyncio.sleep(10**-12)
        async def receive():
            output_stream = p.open(
                format=FORMAT, channels=CHANNELS, rate=OUTPUT_RATE, output=True, frames_per_buffer=CHUNK)
            async for message in session.receive():
                if message.server_content.input_transcription:
                  print(message.server_content.model_dump(mode="json", exclude_none=True))
                if message.server_content.output_transcription:
                  print(message.server_content.model_dump(mode="json", exclude_none=True))
                if message.server_content.model_turn:
                    for part in message.server_content.model_turn.parts:
                        if part.inline_data.data:
                            audio_data=part.inline_data.data
                            output_stream.write(audio_data)
                            await asyncio.sleep(10**-12)
        send_task = asyncio.create_task(send())
        receive_task = asyncio.create_task(receive())
        await asyncio.gather(send_task, receive_task)

asyncio.run(main())
