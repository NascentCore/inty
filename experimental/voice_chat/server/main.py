import asyncio
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    MediaStreamTrack,
    RTCConfiguration,
    RTCIceServer,
)
from starlette.responses import JSONResponse

from google.genai import types
import google.genai as genai
from fractions import Fraction

from .config import load_config

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = load_config()


class SDP(BaseModel):
    sdp: str
    type: str


async def _consume_uplink(track: MediaStreamTrack, out_queue: asyncio.Queue):
    """Continuously read audio frames from incoming WebRTC track and push to queue."""
    while True:
        frame = await track.recv()
        await out_queue.put(frame)


class DownlinkAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, in_queue: asyncio.Queue, sample_rate: int):
        super().__init__()
        self._in_queue = in_queue
        self._sample_rate = sample_rate
        self._ts = 0

    async def recv(self):
        # Wait for incoming frames (already aiortc frames)
        frame = await self._in_queue.get()
        # Ensure timing information present
        if getattr(frame, "pts", None) is None:
            try:
                num_samples = frame.samples
            except Exception:
                num_samples = len(frame.planes[0]) // 2
            frame.pts = self._ts
            frame.time_base = Fraction(1, self._sample_rate)
            self._ts += num_samples
        return frame


class SessionState:
    def __init__(self):
        self.pc: Optional[RTCPeerConnection] = None
        self.uplink_queue: asyncio.Queue = asyncio.Queue(maxsize=20)
        self.downlink_queue: asyncio.Queue = asyncio.Queue(maxsize=20)
        self.bridge_task: Optional[asyncio.Task] = None
        self.audio_sender = None


sessions: Dict[str, SessionState] = {}


@app.post("/offer")
async def offer(sdp: SDP):
    ice_config = RTCConfiguration(
        iceServers=[RTCIceServer(urls=[config.server.stun_server])]
    )
    pc = RTCPeerConnection(ice_config)
    session = SessionState()
    session.pc = pc

    # Configure STUN
    # Note: aiortc takes ICE servers in RTCPeerConnection(configuration=...) but not essential for LAN demo

    @pc.on("track")
    def on_track(track: MediaStreamTrack):
        if track.kind == "audio":
            # Start consuming uplink frames
            asyncio.create_task(_consume_uplink(track, session.uplink_queue))
            # start the Gemini bridge when first audio arrives
            if session.bridge_task is None:
                session.bridge_task = asyncio.create_task(gemini_bridge(session))

    # Set remote
    try:
        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp.sdp, type=sdp.type))
    except Exception as e:
        await pc.close()
        raise HTTPException(status_code=400, detail=f"setRemoteDescription failed: {e}")

    # Add downlink audio track so client can receive audio
    pc.addTrack(
        DownlinkAudioTrack(
            session.downlink_queue, sample_rate=config.gemini.receive_sample_rate
        )
    )

    # Create and set local
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Wait for ICE gathering to complete (no trickle ICE in this simple demo)
    if pc.iceGatheringState != "complete":
        ice_complete = asyncio.Future()

        @pc.on("icegatheringstatechange")
        def _():
            if pc.iceGatheringState == "complete" and not ice_complete.done():
                ice_complete.set_result(True)

        await ice_complete

    return JSONResponse(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )


async def gemini_bridge(session: SessionState):
    """Bridge uplink aiortc audio frames to Gemini Live and push returned audio to downlink.
    This is a minimal demo; proper resampling/encoding and VAD should be added for production.
    """
    client = genai.Client()

    model = config.gemini.model
    voice = config.gemini.voice_name

    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )

    async with client.aio.live.connect(model=model, config=live_config) as session_live:

        async def uplink():
            while True:
                frame = await session.uplink_queue.get()
                # Convert to 16k mono PCM bytes
                # aiortc provides audio frames as av.AudioFrame
                import av

                # Resample to configured rate and mono using PyAV
                resampler = av.audio.resampler.AudioResampler(
                    format="s16",
                    layout="mono",
                    rate=config.gemini.send_sample_rate,
                )
                # Ensure frame format for resampler
                # Some frames may be planar; resampler handles it
                out_frames = resampler.resample(frame)
                if not isinstance(out_frames, list):
                    out_frames = [out_frames]
                buffers = []
                for f in out_frames:
                    buffers.append(bytes(f.planes[0]))
                data = b"".join(buffers)
                await session_live.send(
                    input={
                        "data": data,
                        "mime_type": f"audio/pcm;rate={config.gemini.send_sample_rate}",
                    }
                )

        async def downlink():
            while True:
                turn = session_live.receive()
                async for response in turn:
                    if response.data:
                        # PCM bytes at 24kHz from Gemini
                        # We create a new aiortc AudioFrame from bytes
                        from av.audio.frame import AudioFrame

                        # Create frame: s16, mono, 24000
                        samples = response.data
                        num_samples = len(samples) // 2
                        frame = AudioFrame(
                            format="s16", layout="mono", samples=num_samples
                        )
                        frame.sample_rate = config.gemini.receive_sample_rate
                        # Write planes
                        plane = frame.planes[0]
                        plane.update(samples)

                        await session.downlink_queue.put(frame)
                    if response.text:
                        # Optional: print text
                        print(response.text, end="")

        async with asyncio.TaskGroup() as tg:
            tg.create_task(uplink())
            tg.create_task(downlink())


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
