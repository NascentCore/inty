import os
import time
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play

load_dotenv()
print(os.getenv("ELEVENLABS_API_KEY"))
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

MP3_22KHZ_32KBPS = "mp3_22050_32"
MODEL_ID = "eleven_flash_v2_5"
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

# Eleven V3 style prompting [enthusiastic]Hello! is not available in other models.
# For more control mechanisms, see:
# https://elevenlabs.io/docs/best-practices/prompting/controls
TEXT = """<break time="1.5s" /> Hello! This is a test of the ElevenLabs text to speech API."""

start_time = time.time()
audio_stream = client.text_to_speech.convert(
    text=TEXT,
    voice_id=VOICE_ID,
    model_id=MODEL_ID,
    output_format=MP3_22KHZ_32KBPS,
)
audio_bytes = b"".join(audio_stream)
end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")


with open(f"audio_{MP3_22KHZ_32KBPS}.mp3", "wb") as f:
    f.write(audio_bytes)

play(audio_bytes)
