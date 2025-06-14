import os
from elevenlabs import generate, play, set_api_key
from dotenv import load_dotenv

load_dotenv()

# Set your API key from environment variable
set_api_key(os.getenv('ELEVENLABS_API_KEY'))

def text_to_speech(text):
    # Generate audio from text
    audio = generate(
        text=text,
        voice="Rachel",  # You can change this to any available voice
        model="eleven_monolingual_v1"
    )
    
    # Play the generated audio
    play(audio)

if __name__ == "__main__":
    # Example usage
    text_to_speech("Hello! This is a test of the ElevenLabs text to speech API.")
