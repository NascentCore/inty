# Minimal SSE Example

This folder contains a minimal Server-Sent Events example:

- `server/`: Python FastAPI server exposing `/stream` (SSE) and `/publish` (POST) endpoints
- `android_client/`: Minimal Android app subscribing to SSE via OkHttp and sending messages

## Run Server

```bash
cd experimental/sse/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Android client

Open `experimental/sse/android_client` with Android Studio and run on emulator.

Default server base is `http://10.0.2.2:8009` for Android emulator.
