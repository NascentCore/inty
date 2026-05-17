"""CLI：调用 MiniMax 同步 T2A HTTP 与音乐生成 API，将 hex 音频落盘为 mp3。"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import cyclopts
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 官方 OpenAPI 摘要：https://platform.minimax.io/docs/api-reference/speech-t2a-http.md
# 音乐：https://platform.minimax.io/docs/api-reference/music-generation.md
# 入口介绍页（产品侧）：https://www.minimax.io/audio

API_BASE = "https://api.minimax.io"
T2A_PATH = "/v1/t2a_v2"
MUSIC_PATH = "/v1/music_generation"


class VoiceSetting(BaseModel):
    """T2A voice_setting 子结构（成功路径最小字段集）。"""

    voice_id: str
    speed: float = 1.0
    vol: float = 1.0
    pitch: int = 0


class T2AAudioSetting(BaseModel):
    """T2A audio_setting 子结构。"""

    sample_rate: int = 32000
    bitrate: int = 128000
    format: str = "mp3"
    channel: int = 1


class T2AHttpRequest(BaseModel):
    """POST /v1/t2a_v2 请求体（非流式 + hex 输出）。"""

    model: str = "speech-02-hd"
    text: str
    stream: bool = False
    language_boost: str = "Chinese"
    output_format: str = "hex"
    voice_setting: VoiceSetting
    audio_setting: T2AAudioSetting = Field(default_factory=T2AAudioSetting)


class MusicAudioSetting(BaseModel):
    """音乐 audio_setting。"""

    sample_rate: int = 44100
    bitrate: int = 128000
    format: str = "mp3"


class MusicGenerationRequest(BaseModel):
    """POST /v1/music_generation：纯器乐 + 免费档模型，避免歌词配额演示成本。"""

    model: str = "music-2.6-free"
    prompt: str
    is_instrumental: bool = True
    stream: bool = False
    output_format: str = "hex"
    audio_setting: MusicAudioSetting = Field(default_factory=MusicAudioSetting)


def _repo_relative_outputs_dir() -> Path:
    d = Path(__file__).resolve().parent / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_env() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")


def _bearer_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['MINIMAX_API_KEY']}",
        "Content-Type": "application/json",
    }


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_hex_mp3(hex_audio: str, path: Path) -> None:
    path.write_bytes(bytes.fromhex(hex_audio))


app = cyclopts.App(
    help="MiniMax 音频 API 最小演示（T2A HTTP + music_generation）"
)


@app.command
def tts(
    text: str = "你好，这是 MiniMax 同步语音演示。",
    voice_id: str = "Chinese (Mandarin)_Lyrical_Voice",
    output: str | None = None,
) -> None:
    """同步 HTTP 文本转语音，默认写 ``outputs/minimax_tts_<UTC>.mp3``。"""
    _load_env()
    body = T2AHttpRequest(
        text=text,
        voice_setting=VoiceSetting(voice_id=voice_id),
    )
    out = (
        Path(output)
        if output
        else _repo_relative_outputs_dir() / f"minimax_tts_{_utc_stamp()}.mp3"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=API_BASE, timeout=120.0) as client:
        r = client.post(
            T2A_PATH, headers=_bearer_headers(), json=body.model_dump()
        )
    payload = r.json()
    hex_audio = payload["data"]["audio"]
    _write_hex_mp3(hex_audio, out)
    print(out)


@app.command
def music(
    prompt: str = "Ambient electronic, soft pads, minimal percussion, 90 BPM",
    output: str | None = None,
) -> None:
    """音乐生成（器乐 + music-2.6-free），默认写 ``outputs/minimax_music_<UTC>.mp3``。"""
    _load_env()
    body = MusicGenerationRequest(prompt=prompt)
    out = (
        Path(output)
        if output
        else _repo_relative_outputs_dir() / f"minimax_music_{_utc_stamp()}.mp3"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=API_BASE, timeout=600.0) as client:
        r = client.post(
            MUSIC_PATH, headers=_bearer_headers(), json=body.model_dump()
        )
    payload = r.json()
    hex_audio = payload["data"]["audio"]
    _write_hex_mp3(hex_audio, out)
    print(out)


if __name__ == "__main__":
    app()
