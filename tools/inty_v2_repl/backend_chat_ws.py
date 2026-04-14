"""Client for Inty backend ``/api/v1/chat/ws`` (companion kernel, one JSON frame per turn)."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import uuid
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from app.schemas.chat import ChatCompletionRequest, ChatMessage, ChatWebSocketRequest
from loguru import logger


class BackendChatWsError(RuntimeError):
    def __init__(self, code: int, message: str, agent_id: str | None = None):
        self.code = code
        self.agent_message = message
        self.agent_id = agent_id
        super().__init__(f"chat ws error code={code} message={message!r}")


def http_base_to_ws_chat_url(http_base: str) -> str:
    base = http_base.strip().rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_base}/api/v1/chat/ws"


def _parse_chat_response_payload(data: dict[str, Any]) -> str:
    if data.get("type") == "pong":
        raise ValueError("unexpected pong in response queue")
    code = data.get("code")
    if code is None:
        raise ValueError(f"chat ws response missing code: {data!r}")
    if code != 200:
        msg = data.get("message")
        if not isinstance(msg, str):
            msg = str(msg)
        aid = data.get("agent_id")
        raise BackendChatWsError(int(code), msg, agent_id=str(aid) if aid is not None else None)
    inner = data.get("data") or {}
    choices = inner.get("choices") or []
    if not choices:
        raise ValueError(f"chat ws success but no choices: {data!r}")
    msg0 = (choices[0] or {}).get("message") or {}
    content = msg0.get("content")
    if not isinstance(content, str):
        raise ValueError(f"chat ws assistant content not a string: {content!r}")
    return content


def default_api_base_url() -> str:
    return os.environ.get("INTY_API_BASE_URL", "http://127.0.0.1:8000").strip()


def default_ping_interval_sec() -> float:
    raw = os.environ.get("INTY_V2_BACKEND_WS_PING_INTERVAL_SEC", "25").strip()
    try:
        v = float(raw)
    except ValueError:
        return 25.0
    return max(5.0, min(v, 300.0))


def default_recv_timeout_sec() -> float:
    raw = os.environ.get("INTY_V2_BACKEND_WS_RECV_TIMEOUT_SEC", "600").strip()
    try:
        v = float(raw)
    except ValueError:
        return 600.0
    return max(30.0, min(v, 3600.0))


class BackendChatWsBridge:
    """
    One WebSocket connection on a dedicated asyncio loop (background thread).
    Multiplexes JSON ``ping``/``pong`` with chat completion responses via a reader task.
    """

    def __init__(self, *, ws_url: str, bearer_token: str) -> None:
        self._ws_url = ws_url
        self._bearer_token = bearer_token.strip()
        if not self._bearer_token:
            raise ValueError("bearer_token is empty")
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws: Any = None
        self._response_q: asyncio.Queue[dict[str, Any]] | None = None
        self._halt: asyncio.Event | None = None
        self._ready = threading.Event()
        self._start_error: BaseException | None = None
        self._ping_interval = default_ping_interval_sec()
        self._recv_timeout = default_recv_timeout_sec()

    def start(self, *, connect_timeout: float = 30.0) -> None:
        if self._thread is not None:
            raise RuntimeError("BackendChatWsBridge already started")
        self._ready.clear()
        self._start_error = None

        def thread_main() -> None:
            loop: asyncio.AbstractEventLoop | None = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                loop.run_until_complete(self._run_session(connect_timeout=connect_timeout))
            except BaseException as exc:
                self._start_error = exc
                logger.exception("backend chat ws thread failed: {}", exc)
            finally:
                if loop is not None:
                    try:
                        pending = asyncio.all_tasks(loop)
                        for t in pending:
                            t.cancel()
                        if pending:
                            loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True)
                            )
                    except BaseException:
                        pass
                    loop.close()
                self._loop = None
                self._ws = None
                self._ready.set()

        self._thread = threading.Thread(target=thread_main, name="inty-v2-chat-ws", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=connect_timeout + 15.0):
            self.stop()
            raise TimeoutError("WebSocket connect wait timed out")
        if self._start_error is not None:
            self.stop()
            raise self._start_error
        if not self._loop or not self._ws:
            self.stop()
            raise RuntimeError("WebSocket failed to start (no connection)")

    async def _run_session(self, *, connect_timeout: float) -> None:
        headers = [("Authorization", f"Bearer {self._bearer_token}")]
        halt = asyncio.Event()
        self._halt = halt
        ws = await websockets.connect(
            self._ws_url,
            additional_headers=headers,
            open_timeout=connect_timeout,
            ping_interval=None,
        )
        self._ws = ws
        self._response_q = asyncio.Queue()
        reader = asyncio.create_task(self._read_loop(ws))
        pinger = asyncio.create_task(self._pinger_loop(ws, halt))
        self._ready.set()
        try:
            await halt.wait()
        finally:
            pinger.cancel()
            reader.cancel()
            try:
                await pinger
            except asyncio.CancelledError:
                pass
            except BaseException:
                logger.exception("pinger task exit")
            try:
                await reader
            except asyncio.CancelledError:
                pass
            except BaseException:
                logger.exception("reader task exit")
            await ws.close()
            self._ws = None
            self._halt = None

    async def _read_loop(self, ws: Any) -> None:
        assert self._response_q is not None
        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("chat ws non-json frame skipped len={}", len(raw))
                    continue
                if data.get("type") == "pong":
                    continue
                if data.get("type") == "client_context_ack":
                    continue
                if "code" in data:
                    await self._response_q.put(data)
                    continue
                logger.warning("chat ws unexpected json keys={}", list(data.keys())[:12])
        except ConnectionClosed as e:
            logger.info("chat ws read loop closed: {}", e)
        except asyncio.CancelledError:
            raise

    async def _pinger_loop(self, ws: Any, halt: asyncio.Event) -> None:
        try:
            while not halt.is_set():
                try:
                    await asyncio.wait_for(halt.wait(), timeout=self._ping_interval)
                    return
                except TimeoutError:
                    pass
                if halt.is_set():
                    return
                try:
                    await ws.send(json.dumps({"type": "ping"}))
                except ConnectionClosed:
                    return
        except asyncio.CancelledError:
            raise

    def stop(self) -> None:
        if self._loop is not None and self._loop.is_running() and self._halt is not None:
            if not self._halt.is_set():
                self._loop.call_soon_threadsafe(self._halt.set)
        if self._thread is not None:
            self._thread.join(timeout=15.0)
            self._thread = None

    def send_turn(self, agent_id: str, user_text: str) -> str:
        if not self._loop:
            raise RuntimeError("bridge not started")
        coro = self._send_turn_async(agent_id, user_text)
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=self._recv_timeout + 30.0)

    async def _send_turn_async(self, agent_id: str, user_text: str) -> str:
        if not self._ws or not self._response_q:
            raise RuntimeError("websocket not connected")
        req = ChatWebSocketRequest(
            agent_id=agent_id,
            request=ChatCompletionRequest(
                messages=[ChatMessage(role="user", content=user_text)],
                message_id=str(uuid.uuid4()),
            ),
        )
        await self._ws.send(req.model_dump_json(by_alias=True))
        while True:
            data = await asyncio.wait_for(self._response_q.get(), timeout=self._recv_timeout)
            try:
                return _parse_chat_response_payload(data)
            except ValueError as e:
                logger.warning("chat ws skipped unexpected payload: {}", e)


async def chat_turn_single_http_base(
    *,
    http_base: str,
    bearer_token: str,
    agent_id: str,
    user_text: str,
    connect_timeout: float = 30.0,
) -> str:
    url = http_base_to_ws_chat_url(http_base)
    headers = [("Authorization", f"Bearer {bearer_token.strip()}")]
    recv_timeout = default_recv_timeout_sec()
    async with websockets.connect(
        url,
        additional_headers=headers,
        open_timeout=connect_timeout,
        ping_interval=None,
    ) as ws:
        req = ChatWebSocketRequest(
            agent_id=agent_id,
            request=ChatCompletionRequest(
                messages=[ChatMessage(role="user", content=user_text)],
                message_id=str(uuid.uuid4()),
            ),
        )
        await ws.send(req.model_dump_json(by_alias=True))
        raw = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
        data = json.loads(raw)
        if data.get("type") == "pong":
            raw2 = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
            data = json.loads(raw2)
        return _parse_chat_response_payload(data)
