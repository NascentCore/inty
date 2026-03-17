# GPT Live Voice Call Demo (OpenAI Realtime API)

Terminal-based voice call demo using OpenAI realtime models:
- microphone audio streams to GPT model
- model audio streams back to your speakers
- live transcript is printed in terminal

## 1) Setup

```bash
cd experimental/s2s
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and replace:

```bash
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
```

with your real OpenAI key.

## 2) Run

```bash
cd experimental/s2s
source .venv/bin/activate
python main.py
```

Press `Ctrl+C` to stop the call.

## Optional config

All optional values can be set in `.env`:

- `OPENAI_REALTIME_MODEL` (default: `gpt-4o-realtime-preview`)
- `OPENAI_REALTIME_VOICE` (default: `alloy`)
- `OPENAI_REALTIME_INSTRUCTIONS` (default: friendly phone-call style assistant)

## Files

- `main.py`: primary entrypoint for GPT live voice call demo
- `demo.py`: compatibility wrapper that calls `main.py`
- `audio_util.py`: audio player helpers (adapted from OpenAI realtime example)
- `test_setup.py` and `test_audio.py`: local environment/audio checks

## References

- https://github.com/openai/openai-python/blob/main/examples/realtime/push_to_talk_app.py
