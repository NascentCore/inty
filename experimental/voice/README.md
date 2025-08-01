# TTS (Text to Speech) Demos

## Gemini

`uv run --no-project gemini.py` You might need to install additional deps.
This will write out a `.wav` file that can be played.

## ElevenLabs Demo

Using ElevenLabs API to turn text into speech.

```bash
# Copy API Key from https://tricorder.feishu.cn/wiki/ToKJwUzKiicUf6kZOugcjRbZnih
cp .env.example .env
brew install ffmpeg
python -m venv .venv
pip install -r requirements.txt
python tts/elevenlabs.py
```

The delay is about 1 second. Not too bad.

Demo of <https://elevenlabs.io/v3>, can you tag to influence the speech mode.

![image](https://github.com/user-attachments/assets/3a2963a4-deb6-4451-8562-e4edb591bd68)

### Void library

https://elevenlabs.io/app/voice-library

<img width="3022" height="1804" alt="image" src="https://github.com/user-attachments/assets/bf055def-3f5b-4e8e-aebf-33d6b23eb296" />

### Audio format

Cursor generated with the following prompt on elevenalbs SDK
audio format listing:

```text
What's the differences between these audio format?
```

MP3 Formats:
- **mp3_22050_32**: 22.05 kHz sample rate, 32 kbps bitrate - Lower quality, smaller file size
- **mp3_44100_32**: 44.1 kHz sample rate, 32 kbps bitrate - CD quality sample rate, but low bitrate
- **mp3_44100_64**: 44.1 kHz sample rate, 64 kbps bitrate - Better quality than 32 kbps
- **mp3_44100_96**: 44.1 kHz sample rate, 96 kbps bitrate - Good quality for most use cases
- **mp3_44100_128**: 44.1 kHz sample rate, 128 kbps bitrate - Standard quality, widely compatible
- **mp3_44100_192**: 44.1 kHz sample rate, 192 kbps bitrate - High quality, larger file size

PCM Formats (Uncompressed):
- **pcm_8000**: 8 kHz sample rate - Telephone quality, very small files
- **pcm_16000**: 16 kHz sample rate - Better than telephone, good for speech
- **pcm_22050**: 22.05 kHz sample rate - Standard for web audio
- **pcm_24000**: 24 kHz sample rate - Good for speech applications
- **pcm_44100**: 44.1 kHz sample rate - CD quality, uncompressed
- **pcm_48000**: 48 kHz sample rate - Professional audio quality

Compressed Formats:
- **ulaw_8000**: μ-law compression at 8 kHz - Telephone standard
- **alaw_8000**: A-law compression at 8 kHz - European telephone standard

Opus Formats (Modern, Efficient):
- **opus_48000_32**: 48 kHz sample rate, 32 kbps - Very efficient compression
- **opus_48000_64**: 48 kHz sample rate, 64 kbps - Good quality, small size
- **opus_48000_96**: 48 kHz sample rate, 96 kbps - High quality
- **opus_48000_128**: 48 kHz sample rate, 128 kbps - Excellent quality
- **opus_48000_192**: 48 kHz sample rate, 192 kbps - Maximum quality

Recommendations:
- **For web/speech**: `mp3_22050_32` (your current choice) - good balance of quality and size
- **For high quality**: `mp3_44100_128` or `opus_48000_128`
- **For maximum compatibility**: `mp3_44100_128`
- **For smallest file size**: `opus_48000_32`
- **For professional use**: `pcm_48000` (uncompressed, largest files)

Current choice of `mp3_22050_32` is quite good for speech applications as it provides adequate quality while keeping file sizes small!
