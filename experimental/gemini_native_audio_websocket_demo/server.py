"""
Gemini Native Audio WebSocket Demo Server

CREATED_BY_AGENT
"""

import asyncio
import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from loguru import logger

DEBUG_LOG_PATH = "/Users/donggang/Documents/code/inty-backend/.cursor/debug.log"

PROJECT_ID = "alien-paratext-461204-i9"
LOCATION = "us-central1"
MODEL = "gemini-live-2.5-flash-native-audio"
VOICE = "Zephyr"
SEND_SAMPLE_RATE = 16000


def debug_log(
    *, run_id: str, location: str, message: str, data: dict, hypothesis_id: str
):
    payload = {
        "timestamp": int(time.time() * 1000),
        "sessionId": "debug-session",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
    }
    # #region agent log
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion


def _resolve_credentials() -> None:
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    candidates = [
        "/Users/donggang/Documents/code/inty-backend/inty-backend-key.json",
        "/Users/donggang/Documents/code/inty-backend/.secrets/gcp-service-account-key.json",
        "/Users/donggang/Documents/code/inty-backend/devops/gcp-service-account-key.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = p
            return


@dataclass
class LiveBridge:
    client: genai.Client
    config: types.LiveConnectConfig
    mode: str  # "single" | "reconnect"
    run_id: str

    cm: Any = None
    session: Any = None
    receive_task: Optional[asyncio.Task] = None
    lock: asyncio.Lock = asyncio.Lock()

    async def open(self):
        await self._open_new_session(reason="initial")

    async def close(self):
        if self.receive_task is not None:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        if self.cm is not None:
            try:
                await self.cm.__aexit__(None, None, None)
            except Exception:
                pass

    async def _open_new_session(self, *, reason: str):
        # #region agent log
        debug_log(
            run_id=self.run_id,
            location="demo_server.py:reconnect_start",
            message="open_new_session",
            data={"reason": reason, "mode": self.mode},
            hypothesis_id="DEMO",
        )
        # #endregion

        cm = self.client.aio.live.connect(model=MODEL, config=self.config)
        live_session = await cm.__aenter__()

        old_cm = self.cm
        old_task = self.receive_task

        async with self.lock:
            self.cm = cm
            self.session = live_session
            self.receive_task = None

        if old_task is not None:
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass

        if old_cm is not None:
            try:
                await old_cm.__aexit__(None, None, None)
            except Exception:
                pass

        # #region agent log
        debug_log(
            run_id=self.run_id,
            location="demo_server.py:reconnect_ok",
            message="open_new_session_ok",
            data={"reason": reason, "mode": self.mode},
            hypothesis_id="DEMO",
        )
        # #endregion

    async def ensure_receive_loop(self, websocket: WebSocket):
        async with self.lock:
            if self.receive_task is not None:
                return
            live_session = self.session

        async def _recv():
            turn_complete_count = 0
            try:
                async for msg in live_session.receive():
                    sc = getattr(msg, "server_content", None)
                    if not sc:
                        continue

                    mt = getattr(sc, "model_turn", None)
                    if mt:
                        for part in mt.parts:
                            inline = getattr(part, "inline_data", None)
                            if inline and getattr(inline, "data", None):
                                await websocket.send_text(
                                    json.dumps(
                                        {
                                            "type": "audio",
                                            "data": base64.b64encode(
                                                inline.data
                                            ).decode("utf-8"),
                                            "mime_type": inline.mime_type,
                                        }
                                    )
                                )

                    if getattr(sc, "turn_complete", False):
                        turn_complete_count += 1
                        # #region agent log
                        debug_log(
                            run_id=self.run_id,
                            location="demo_server.py:turn_complete",
                            message="turn_complete",
                            data={
                                "count": turn_complete_count,
                                "mode": self.mode,
                            },
                            hypothesis_id="DEMO",
                        )
                        # #endregion

                        await websocket.send_text(
                            json.dumps(
                                {"type": "status", "status": "turn_complete"}
                            )
                        )

                        if self.mode == "reconnect":
                            # 关键：每轮重连，绕过 #1224
                            await self._open_new_session(reason="turn_complete")
                            return

            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning(f"receive loop error: {e}")
                await websocket.send_text(
                    json.dumps({"type": "error", "message": str(e)})
                )

        task = asyncio.create_task(_recv())
        async with self.lock:
            self.receive_task = task

    async def send_audio(self, pcm16_bytes: bytes):
        async with self.lock:
            live_session = self.session
        if live_session is None:
            return
        await live_session.send_realtime_input(
            audio=types.Blob(
                data=pcm16_bytes,
                mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
            )
        )


def _build_live_config(*, silence_ms: int) -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=VOICE
                )
            )
        ),
        system_instruction="You are a helpful assistant. Keep your responses very short.",
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                prefix_padding_ms=20,
                silence_duration_ms=silence_ms,
            )
        ),
    )


app = FastAPI(title="Gemini Native Audio WebSocket Demo")
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()

    mode = websocket.query_params.get("mode", "single")
    if mode not in ("single", "reconnect"):
        mode = "single"

    silence_ms_str = websocket.query_params.get("silence_ms", "500")
    try:
        silence_ms = int(silence_ms_str)
    except Exception:
        silence_ms = 500
    if silence_ms < 50:
        silence_ms = 50
    if silence_ms > 5000:
        silence_ms = 5000

    run_id = f"demo_{int(time.time())}"
    _resolve_credentials()
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    config = _build_live_config(silence_ms=silence_ms)
    bridge = LiveBridge(client=client, config=config, mode=mode, run_id=run_id)

    debug_log(
        run_id=run_id,
        location="demo_server.py:ws_open",
        message="ws_open",
        data={"mode": mode, "silence_ms": silence_ms},
        hypothesis_id="DEMO",
    )

    try:
        await bridge.open()
        await bridge.ensure_receive_loop(websocket)
        await websocket.send_text(
            json.dumps({"type": "status", "status": "connected"})
        )

        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "audio":
                data_b64 = msg.get("data", "")
                if not data_b64:
                    continue
                pcm = base64.b64decode(data_b64)
                await bridge.send_audio(pcm)
                await bridge.ensure_receive_loop(websocket)
            elif msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg.get("type") == "end":
                break
            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "unknown message"})
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(e)
    finally:
        debug_log(
            run_id=run_id,
            location="demo_server.py:ws_close",
            message="ws_close",
            data={"mode": mode},
            hypothesis_id="DEMO",
        )
        await bridge.close()
