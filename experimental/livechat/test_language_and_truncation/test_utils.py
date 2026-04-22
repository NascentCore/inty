"""
共享工具: WebSocket 客户端、音频处理、结果记录

Usage:
    from test_utils import IntyLiveChatClient, load_wav_pcm, wav_info
"""

import asyncio
import base64
import json
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import websockets

TEST_RESULTS_DIR = Path(__file__).resolve().parent / "test_results"
SEND_SAMPLE_RATE = 16000
SEND_CHUNK_MS = 20  # 每块 20ms
SEND_CHUNK_SIZE = int(SEND_SAMPLE_RATE * 2 * SEND_CHUNK_MS / 1000)  # 640 bytes
# 真机麦克风会持续推送含静音的 PCM；服务端 VAD silence_duration_ms=800，尾随静音帮助判句尾
DEFAULT_TRAILING_SILENCE_MS = 1000


@dataclass
class TranscriptEvent:
    """转录事件"""

    timestamp: float
    role: str  # "user" | "assistant"
    text: str
    message_id: Optional[int] = None


@dataclass
class StatusEvent:
    """状态事件"""

    timestamp: float
    status: str
    message: Optional[str] = None


@dataclass
class ErrorEvent:
    """错误事件"""

    timestamp: float
    code: Optional[int] = None
    error_code: Optional[str] = None
    message: Optional[str] = None


@dataclass
class SessionLog:
    """会话日志"""

    session_start: float = field(default_factory=time.time)
    transcripts: list[TranscriptEvent] = field(default_factory=list)
    statuses: list[StatusEvent] = field(default_factory=list)
    errors: list[ErrorEvent] = field(default_factory=list)
    audio_count: int = 0
    ai_audio_bytes: int = 0
    session_info: dict = field(default_factory=dict)

    def add_transcript(self, role: str, text: str, message_id: Optional[int] = None):
        self.transcripts.append(
            TranscriptEvent(
                timestamp=time.time(),
                role=role,
                text=text,
                message_id=message_id,
            )
        )

    def add_status(self, status: str, message: Optional[str] = None):
        self.statuses.append(
            StatusEvent(
                timestamp=time.time(),
                status=status,
                message=message,
            )
        )

    def add_error(self, code=None, error_code=None, message=None):
        self.errors.append(
            ErrorEvent(
                timestamp=time.time(),
                code=code,
                error_code=error_code,
                message=message,
            )
        )


def load_wav_pcm(wav_path: Path) -> bytes:
    """读取 WAV 文件并返回原始 PCM16 数据"""
    with wave.open(str(wav_path), "rb") as wf:
        return wf.readframes(wf.getnframes())


def wav_info(wav_path: Path) -> dict:
    """获取 WAV 文件信息"""
    with wave.open(str(wav_path), "rb") as wf:
        pcm = wf.readframes(wf.getnframes())
        return {
            "path": str(wav_path),
            "sample_rate": wf.getframerate(),
            "channels": wf.getnchannels(),
            "sample_width": wf.getsampwidth(),
            "duration_ms": len(pcm) / (wf.getframerate() * wf.getsampwidth()) * 1000,
            "frames": wf.getnframes(),
        }


def chunk_pcm(pcm_data: bytes, chunk_size: int = SEND_CHUNK_SIZE) -> list[bytes]:
    """将 PCM 数据按固定大小分块"""
    return [pcm_data[i : i + chunk_size] for i in range(0, len(pcm_data), chunk_size)]


class IntyLiveChatClient:
    """inty-backend Live Chat WebSocket 客户端"""

    def __init__(
        self,
        base_url: str = "ws://localhost:8000",
        token: str = "",
        agent_id: str = "",
        speech_language_code: Optional[str] = None,
        response_language_name: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.agent_id = agent_id
        self.speech_language_code = speech_language_code
        self.response_language_name = response_language_name
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._log = SessionLog()
        self._receive_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()

    @property
    def log(self) -> SessionLog:
        return self._log

    @property
    def ws_url(self) -> str:
        """构建 WebSocket URL"""
        url = f"{self.base_url}/api/v1/live-chat/{self.agent_id}?token={self.token}"
        if self.speech_language_code:
            url += f"&speech_language_code={self.speech_language_code}"
        if self.response_language_name:
            url += f"&response_language_name={self.response_language_name}"
        return url

    async def connect(self) -> bool:
        """连接并开始接收消息"""
        try:
            self._ws = await websockets.connect(self.ws_url)
        except Exception as e:
            print(f"WebSocket 连接失败: {e}")
            return False

        self._receive_task = asyncio.create_task(self._receive_loop())
        return True

    async def disconnect(self):
        """断开连接"""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()

    async def send_activity_start(self):
        """与服务端协议一致：显式标记用户开始说话（与 inty_voice_call 可选 API 对齐）。"""
        await self._send_json({"type": "activity_start"})

    async def send_activity_end(self):
        """显式标记用户说完一轮，避免仅发 PCM 后断流导致 Gemini VAD 长期不结束。"""
        await self._send_json({"type": "activity_end"})

    async def send_silence_pcm(
        self,
        duration_ms: int,
        chunk_ms: int = SEND_CHUNK_MS,
    ):
        """发送 16-bit mono 静音 PCM 分块（与语音包相同 chunk 节奏），模拟麦克风尾音。"""
        chunk_size = int(SEND_SAMPLE_RATE * 2 * chunk_ms / 1000)
        silence = b"\x00" * chunk_size
        n = max(1, (duration_ms + chunk_ms - 1) // chunk_ms)
        for _ in range(n):
            await self._send_json(
                {
                    "type": "audio",
                    "data": base64.b64encode(silence).decode("utf-8"),
                }
            )
            await asyncio.sleep(chunk_ms / 1000)

    async def send_audio_wav(
        self,
        wav_path: Path,
        chunk_ms: int = SEND_CHUNK_MS,
        *,
        use_explicit_activity: bool = True,
        trailing_silence_ms: int = DEFAULT_TRAILING_SILENCE_MS,
    ):
        """发送 WAV 音频（16k/mono/int16 PCM）。

        默认在 PCM 前后发送 activity_start / activity_end，与后端 WebSocket 协议一致；
        activity_end 之后再发一段静音 PCM，对齐真机麦克风持续推流行为，便于 VAD 判句尾。
        若需复现纯 VAD、无 activity 时可设 use_explicit_activity=False（发完后 sleep 等静音窗）。
        """
        if use_explicit_activity:
            await self.send_activity_start()

        pcm = load_wav_pcm(wav_path)
        chunk_size = int(SEND_SAMPLE_RATE * 2 * chunk_ms / 1000)

        for chunk in chunk_pcm(pcm, chunk_size):
            await self._send_json(
                {
                    "type": "audio",
                    "data": base64.b64encode(chunk).decode("utf-8"),
                }
            )
            await asyncio.sleep(chunk_ms / 1000)

        if use_explicit_activity:
            await self.send_activity_end()
            if trailing_silence_ms > 0:
                await self.send_silence_pcm(trailing_silence_ms, chunk_ms=chunk_ms)
        else:
            # 纯 VAD：发完音频后等待静音让服务端检测 end_of_speech（silence_duration_ms=800 + buffer）
            await asyncio.sleep(1.2)

        self._log.audio_count += 1

    async def send_text(self, text: str):
        """发送文本消息"""
        await self._send_json({"type": "text", "data": text})

    async def send_end(self):
        """发送结束信号"""
        await self._send_json({"type": "end"})

    async def wait_for_turn_complete(self, timeout: float = 30.0) -> Optional[str]:
        """等待一轮对话完成，返回 AI 转录文本"""
        deadline = time.time() + timeout
        last_ai_text = None
        seen_statuses = set()

        while time.time() < deadline:
            try:
                msg = await asyncio.wait_for(
                    self._message_queue.get(), timeout=deadline - time.time()
                )
            except asyncio.TimeoutError:
                return last_ai_text

            if msg.get("type") == "transcript":
                text = msg.get("text", "")
                self._log.add_transcript("assistant", text, msg.get("message_id"))
                last_ai_text = text
                print(f"  [AI] {text}")

            elif msg.get("type") == "user_transcript":
                text = msg.get("text", "")
                self._log.add_transcript("user", text, msg.get("message_id"))
                print(f"  [USER] {text}")

            elif msg.get("type") == "status":
                status = msg.get("status", "")
                self._log.add_status(status, msg.get("message"))
                seen_statuses.add(status)
                print(f"  [STATUS] {status} {msg.get('message', '') or ''}")

                # LISTENING 状态表示一轮结束（已收到过 AI 转录）
                if status == "listening" and last_ai_text is not None:
                    return last_ai_text

            elif msg.get("type") == "error":
                self._log.add_error(
                    code=msg.get("code"),
                    error_code=msg.get("error_code"),
                    message=msg.get("message"),
                )
                print(f"  [ERROR] {msg}")

            elif msg.get("type") == "session_info":
                self._log.session_info = msg

        return last_ai_text

    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type", "")
                if msg_type == "audio_response":
                    data_b64 = msg.get("data", "")
                    if data_b64:
                        self._log.ai_audio_bytes += len(data_b64)
                await self._message_queue.put(msg)
        except websockets.exceptions.ConnectionClosed:
            pass
        except asyncio.CancelledError:
            pass

    async def _send_json(self, data: dict):
        """发送 JSON 消息"""
        if self._ws:
            await self._ws.send(json.dumps(data))


def save_test_report(name: str, log: SessionLog, extra: Optional[dict] = None):
    """保存测试报告"""
    TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = TEST_RESULTS_DIR / f"{name}_{timestamp}.json"

    report = {
        "test_name": name,
        "timestamp": timestamp,
        "duration_s": round(time.time() - log.session_start, 2),
        "session_info": log.session_info,
        "transcripts": [
            {"role": t.role, "text": t.text, "ts": t.timestamp} for t in log.transcripts
        ],
        "status_sequence": [
            {"status": s.status, "message": s.message, "ts": s.timestamp}
            for s in log.statuses
        ],
        "errors": [
            {"code": e.code, "error_code": e.error_code, "message": e.message}
            for e in log.errors
        ],
        "audio_stats": {
            "chunks_sent": log.audio_count,
            "ai_audio_bytes": log.ai_audio_bytes,
        },
    }
    if extra:
        report["extra"] = extra

    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n测试报告已保存: {path}")
    return path


def detect_language(text: str) -> str:
    """简单检测文本主要语言"""
    cn_chars = sum(1 for c in text if "一" <= c <= "鿿" or "㐀" <= c <= "䶿")
    en_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    if cn_chars > en_chars:
        return "zh"
    elif en_chars > cn_chars:
        return "en"
    return "mixed"


def check_language_mixing(transcripts: list[TranscriptEvent]) -> dict:
    """
    检查转录中是否存在语言混用问题

    返回:
        {
            "has_mixing": bool,
            "mixed_turns": [{"role": ..., "text": ..., "languages": [...]}],
            "summary": str,
        }
    """
    mixed_turns = []
    for t in transcripts:
        if t.role != "assistant":
            continue
        lang = detect_language(t.text)
        if lang == "mixed":
            mixed_turns.append(
                {"role": t.role, "text": t.text, "languages": ["zh", "en"]}
            )

    return {
        "has_mixing": len(mixed_turns) > 0,
        "mixed_turns": mixed_turns,
        "summary": (
            f"发现 {len(mixed_turns)} 个混用语言的 AI 回复"
            if mixed_turns
            else "未发现语言混用"
        ),
    }
