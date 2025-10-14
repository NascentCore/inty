"""
Real-time Voice Chat Demo using Google Gemini Live API

Installation:
# On Linux
sudo apt-get install portaudio19-dev

# On Mac
brew install portaudio

# Install dependencies
pip install google-genai pyaudio

Based on: https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/multimodal-live-api/intro_multimodal_live_api_genai_sdk.ipynb
"""

import asyncio
import signal
import sys
from typing import Optional

import pyaudio
from google.genai import types
from loguru import logger

from app.utils.gemini import get_genai_client

# Audio configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
INPUT_RATE = 16000
OUTPUT_RATE = 24000

# Model configuration
MODEL = 'gemini-2.0-flash-exp'
CONFIG = {
    "response_modalities": ["AUDIO"],
    "input_audio_transcription": {},
    "output_audio_transcription": {},
}

class VoiceChatDemo:
    def __init__(self):
        self.client = get_genai_client()
        self.p = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None
        self.running = False
        
    def setup_audio_streams(self):
        """Setup input and output audio streams"""
        try:
            self.input_stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=INPUT_RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            self.output_stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=OUTPUT_RATE,
                output=True,
                frames_per_buffer=CHUNK
            )
            logger.info("Audio streams initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize audio streams: {e}")
            raise
    
    def cleanup_audio_streams(self):
        """Clean up audio streams"""
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.p.terminate()
        logger.info("Audio streams cleaned up")
    
    async def send_audio(self, session):
        """Continuously send audio data to the session"""
        try:
            while self.running:
                if self.input_stream:
                    # Read audio data from microphone
                    audio_data = self.input_stream.read(CHUNK, exception_on_overflow=False)
                    
                    # Send audio data to Gemini
                    await session.send(input={"data": audio_data, "mime_type": "audio/pcm"})
                    
                    # Small delay to prevent overwhelming the API
                    await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in send_audio: {e}")
    
    async def receive_responses(self, session):
        """Receive and process responses from Gemini"""
        try:
            async for message in session.receive():
                if not self.running:
                    break
                    
                # Handle input transcription (what you said)
                if message.server_content.input_transcription:
                    transcription = message.server_content.input_transcription
                    if transcription.text:
                        print(f"🎤 You: {transcription.text}")
                
                # Handle output transcription (what Gemini said)
                if message.server_content.output_transcription:
                    transcription = message.server_content.output_transcription
                    if transcription.text:
                        print(f"🤖 Gemini: {transcription.text}")
                
                # Handle audio response
                if message.server_content.model_turn:
                    for part in message.server_content.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            # Play the audio response
                            if self.output_stream:
                                self.output_stream.write(part.inline_data.data)
                                
        except Exception as e:
            logger.error(f"Error in receive_responses: {e}")
    
    async def run(self):
        """Main chat loop"""
        print("🎙️  Starting Gemini Voice Chat Demo")
        print("📝 Speak into your microphone to chat with Gemini")
        print("⏹️  Press Ctrl+C to stop")
        print("-" * 50)
        
        self.setup_audio_streams()
        self.running = True
        
        try:
            async with self.client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                logger.info(f"Connected to {MODEL}")
                
                # Start both tasks concurrently
                send_task = asyncio.create_task(self.send_audio(session))
                receive_task = asyncio.create_task(self.receive_responses(session))
                
                # Wait for both tasks to complete
                await asyncio.gather(send_task, receive_task)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.running = False
            self.cleanup_audio_streams()
            print("\n👋 Voice chat ended")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Stopping voice chat...")
    sys.exit(0)

async def main():
    """Main entry point"""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    demo = VoiceChatDemo()
    await demo.run()

if __name__ == "__main__":
    asyncio.run(main())
