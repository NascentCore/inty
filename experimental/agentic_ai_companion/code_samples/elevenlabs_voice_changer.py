# https://elevenlabs.io/docs/eleven-api/guides/cookbooks/voice-changer

# example.py
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
import requests
from io import BytesIO

load_dotenv()

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)
voice_id = "JBFqnCBsd6RMkjVDRZzb"

audio_url = "https://storage.googleapis.com/eleven-public-cdn/audio/marketing/nicole.mp3"
response = requests.get(audio_url)
audio_data = BytesIO(response.content)

audio_stream = elevenlabs.speech_to_speech.convert(
    voice_id=voice_id,
    audio=audio_data,
    model_id="eleven_multilingual_sts_v2",
    output_format="mp3_44100_128",
)

play(audio_stream)
