# TTS (Text to Speech)

Using ElevenLabs API to turn text into speech.

```bash
# Copy API Key from https://tricorder.feishu.cn/wiki/ToKJwUzKiicUf6kZOugcjRbZnih
cp .env.example .env
brew install ffmpeg
python -m venv .venv
pip install -r requirements.txt
python tts_example.py
```

The delay is about 1 second. Not too bad.
