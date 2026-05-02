"""Client for Inty backend ``/api/v1/chat/ws`` (companion kernel, one JSON frame per turn)."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

import websockets
from websockets.exceptions import ConnectionClosed

from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
    ChatWebSocketRequest,
    CompanionChatTurnMessageType,
    normalize_websocket_companion_message_id_uuid,
)
from loguru import logger


class BackendChatWsError(RuntimeError):
    def __init__(self, code: int, message: str, agent_id: str | None = None):
        self.code = code
        self.agent_message = message
        self.agent_id = agent_id
        super().__init__(f"chat ws error code={code} message={message!r}")


def http_base_to_ws_chat_url(http_base: str, *, agent_id: str | None = None) -> str:
    base = http_base.strip().rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    url = f"{ws_base}/api/v1/chat/ws"
    aid = (agent_id or "").strip()
    if aid:
        url = f"{url}?agent_id={aid}"
    return url


def _parse_chat_response_payload(data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
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
    meta_raw = msg0.get("meta_data")
    meta: dict[str, Any] = {}
    if isinstance(meta_raw, dict):
        meta = dict(meta_raw)
    return content, meta


def _agent_id_from_ws_url(ws_url: str) -> str | None:
    parsed = urlparse(ws_url.strip())
    vals = parse_qs(parsed.query).get("agent_id") or []
    if not vals:
        return None
    aid = str(vals[0]).strip()
    return aid or None


def _ws_chat_turn_send_payload(
    agent_id: str,
    user_text: str,
    message_id: str | None,
    *,
    companion_turn_message_type: CompanionChatTurnMessageType = CompanionChatTurnMessageType.USER_MESSAGE,
) -> tuple[str, str]:
    mid = (
        normalize_websocket_companion_message_id_uuid(message_id)
        if message_id and str(message_id).strip()
        else str(uuid.uuid4())
    )
    req = ChatWebSocketRequest(
        agent_id=agent_id,
        request=ChatCompletionRequest(
            messages=[ChatMessage(role="user", content=user_text)],
            message_id=mid,
            message_type=companion_turn_message_type,
        ),
    )
    return mid, req.model_dump_json(by_alias=True)


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


def default_reconnect_initial_sec() -> float:
    raw = os.environ.get("INTY_V2_BACKEND_WS_RECONNECT_INITIAL_SEC", "0.5").strip()
    try:
        v = float(raw)
    except ValueError:
        return 0.5
    return max(0.1, min(v, 120.0))


def default_reconnect_max_sec() -> float:
    raw = os.environ.get("INTY_V2_BACKEND_WS_RECONNECT_MAX_SEC", "20").strip()
    try:
        v = float(raw)
    except ValueError:
        return 20.0
    return max(0.5, min(v, 300.0))


def default_send_turn_retries() -> int:
    raw = os.environ.get("INTY_V2_BACKEND_WS_SEND_RETRIES", "8").strip()
    try:
        v = int(raw)
    except ValueError:
        return 8
    return max(1, min(v, 50))


def default_post_turn_thread_timeout_sec() -> float:
    """Thread-side timeout for ``post_turn`` ``Future.result`` (send-only, includes reconnect waits)."""
    raw = os.environ.get("INTY_V2_BACKEND_WS_POST_TURN_TIMEOUT_SEC", "").strip()
    if raw:
        try:
            v = float(raw)
        except ValueError:
            return 180.0
        return max(30.0, min(v, 3600.0))
    return 180.0


def reconnect_delay_sec(attempt_index: int, *, initial: float, cap: float) -> float:
    base = min(initial * (2**attempt_index), cap)
    return base


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
        self._reconnect_initial = default_reconnect_initial_sec()
        self._reconnect_max = default_reconnect_max_sec()
        self._send_max_retries = default_send_turn_retries()
        self._online_ev: asyncio.Event | None = None
        self._successful_transport_connects: int = 0

    async def _maybe_post_implicit_signed_on_after_reconnect(self) -> None:
        """After transport reconnect, send one IMPLICIT_USER_SIGNED_ON frame when URL pins agent_id."""
        aid = _agent_id_from_ws_url(self._ws_url)
        if not aid:
            return
        deadline = time.monotonic() + max(120.0, float(self._send_max_retries) * 30.0)
        try:
            await self._post_turn_async(
                aid,
                "",
                deadline_monotonic=deadline,
                message_id=str(uuid.uuid4()),
                companion_turn_message_type=CompanionChatTurnMessageType.IMPLICIT_USER_SIGNED_ON,
            )
        except BaseException:
            logger.exception("repl implicit IMPLICIT_USER_SIGNED_ON after reconnect failed")

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

    def try_pop_queued_chat(
        self,
    ) -> tuple[str | None, tuple[int, str] | None, dict[str, Any]]:
        """Non-blocking: pop one queued chat JSON if present (runs on the bridge event loop).

        Returns ``(assistant_text, None, meta_data)`` on success, ``(None, (code, message), {})`` on API error
        frames, ``(None, None, {})`` if the queue was empty or the frame was not a chat completion.
        """
        if not self._loop or not self._response_q:
            return None, None, {}

        async def _pop_raw() -> dict[str, Any] | None:
            q = self._response_q
            if q is None:
                return None
            try:
                return q.get_nowait()
            except asyncio.QueueEmpty:
                return None

        fut = asyncio.run_coroutine_threadsafe(_pop_raw(), self._loop)
        try:
            raw = fut.result(timeout=3.0)
        except Exception:
            return None, None, {}
        if raw is None:
            return None, None, {}
        try:
            text, meta = _parse_chat_response_payload(raw)
            return text, None, meta
        except BackendChatWsError as exc:
            return None, (int(exc.code), str(exc.agent_message)), {}
        except ValueError:
            logger.warning("chat ws queued frame dropped: {}", raw)
            return None, None, {}

    async def _sleep_backoff(self, attempt_index: int, halt: asyncio.Event) -> None:
        delay = reconnect_delay_sec(
            attempt_index, initial=self._reconnect_initial, cap=self._reconnect_max
        )
        logger.info("chat ws reconnect sleeping {:.2f}s", delay)
        end = time.monotonic() + delay
        while time.monotonic() < end:
            if halt.is_set():
                return
            await asyncio.sleep(min(0.2, max(0.0, end - time.monotonic())))

    async def _run_session(self, *, connect_timeout: float) -> None:
        headers = [("Authorization", f"Bearer {self._bearer_token}")]
        halt = asyncio.Event()
        self._halt = halt
        self._online_ev = asyncio.Event()
        reconnect_idx = 0
        try:
            while not halt.is_set():
                self._online_ev.clear()
                self._ws = None
                self._response_q = None
                ws: Any = None
                try:
                    ws = await websockets.connect(
                        self._ws_url,
                        additional_headers=headers,
                        open_timeout=connect_timeout,
                        ping_interval=None,
                    )
                except BaseException as exc:
                    if not self._ready.is_set():
                        raise RuntimeError(f"initial WebSocket connect failed: {exc}") from exc
                    logger.warning("chat ws reconnect connect failed: {}", exc)
                    await self._sleep_backoff(reconnect_idx, halt)
                    reconnect_idx += 1
                    continue
                self._ws = ws
                self._response_q = asyncio.Queue()
                self._online_ev.set()
                connect_seq = self._successful_transport_connects
                self._successful_transport_connects += 1
                if not self._ready.is_set():
                    self._ready.set()
                reconnect_idx = 0
                if connect_seq > 0 and _agent_id_from_ws_url(self._ws_url):
                    asyncio.create_task(self._maybe_post_implicit_signed_on_after_reconnect())
                reader_task = asyncio.create_task(self._read_loop(ws))
                pinger = asyncio.create_task(self._pinger_loop(ws, halt))
                halt_task = asyncio.create_task(halt.wait())
                try:
                    _done, pending = await asyncio.wait(
                        {reader_task, halt_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for t in pending:
                        t.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                finally:
                    pinger.cancel()
                    try:
                        await pinger
                    except asyncio.CancelledError:
                        pass
                    except BaseException:
                        logger.exception("pinger task exit")
                if halt.is_set():
                    reader_task.cancel()
                    try:
                        await reader_task
                    except asyncio.CancelledError:
                        pass
                    except BaseException:
                        logger.exception("reader task exit")
                    try:
                        await ws.close()
                    except BaseException:
                        pass
                    self._ws = None
                    self._online_ev.clear()
                    break
                try:
                    await asyncio.wait_for(reader_task, timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    reader_task.cancel()
                    try:
                        await reader_task
                    except asyncio.CancelledError:
                        pass
                    except BaseException:
                        logger.exception("reader task exit")
                logger.info("chat ws read loop ended; reconnecting")
                try:
                    await ws.close()
                except BaseException:
                    pass
                self._ws = None
                self._response_q = None
                self._online_ev.clear()
                await self._sleep_backoff(reconnect_idx, halt)
                reconnect_idx += 1
        finally:
            self._online_ev.clear()
            self._ws = None
            self._response_q = None
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

    async def _wait_online_async(self, *, deadline_monotonic: float) -> None:
        ev = self._online_ev
        if ev is None or self._halt is None:
            raise RuntimeError("bridge stopped")
        while time.monotonic() < deadline_monotonic:
            if self._halt.is_set():
                raise RuntimeError("bridge stopped")
            if self._ws is not None and self._response_q is not None and ev.is_set():
                return
            try:
                await asyncio.wait_for(ev.wait(), timeout=0.5)
            except TimeoutError:
                continue
        raise TimeoutError("wait for chat WebSocket online timed out")

    async def _post_turn_async(
        self,
        agent_id: str,
        user_text: str,
        *,
        deadline_monotonic: float,
        message_id: str | None = None,
        companion_turn_message_type: CompanionChatTurnMessageType = CompanionChatTurnMessageType.USER_MESSAGE,
    ) -> str:
        """Send one user chat JSON frame; return normalized ``message_id``. No recv."""
        last_transport: BaseException | None = None
        for attempt in range(self._send_max_retries):
            await self._wait_online_async(deadline_monotonic=deadline_monotonic)
            if not self._ws or not self._response_q:
                last_transport = RuntimeError("websocket not connected")
                logger.warning("chat ws not connected before post_turn (attempt {})", attempt)
                continue
            try:
                mid, payload = _ws_chat_turn_send_payload(
                    agent_id,
                    user_text,
                    message_id,
                    companion_turn_message_type=companion_turn_message_type,
                )
                await self._ws.send(payload)
                return mid
            except ConnectionClosed as e:
                last_transport = e
                logger.info(
                    "chat ws ConnectionClosed during post_turn (attempt {})", attempt
                )
                continue
        if last_transport is not None:
            raise RuntimeError(
                f"chat ws post_turn failed after {self._send_max_retries} attempts"
            ) from last_transport
        raise RuntimeError(f"chat ws post_turn failed after {self._send_max_retries} attempts")

    def post_turn(
        self,
        agent_id: str,
        user_text: str,
        message_id: str | None = None,
        *,
        companion_turn_message_type: CompanionChatTurnMessageType = CompanionChatTurnMessageType.USER_MESSAGE,
    ) -> str:
        """Send one turn on the wire and return the normalized ``message_id`` (no wait for assistant)."""
        if not self._loop:
            raise RuntimeError("bridge not started")
        send_budget = float(self._send_max_retries) * (self._reconnect_max + 30.0)
        deadline = time.monotonic() + max(120.0, send_budget)
        coro = self._post_turn_async(
            agent_id,
            user_text,
            deadline_monotonic=deadline,
            message_id=message_id,
            companion_turn_message_type=companion_turn_message_type,
        )
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        thread_timeout = max(120.0, send_budget, default_post_turn_thread_timeout_sec())
        return fut.result(timeout=thread_timeout)

    def send_turn(
        self,
        agent_id: str,
        user_text: str,
        message_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        if not self._loop:
            raise RuntimeError("bridge not started")
        result_cap = (
            self._recv_timeout
            + 45.0
            + float(self._send_max_retries) * (self._reconnect_max + 25.0)
        )
        deadline = time.monotonic() + max(120.0, result_cap)
        coro = self._send_turn_async(
            agent_id,
            user_text,
            deadline_monotonic=deadline,
            message_id=message_id,
        )
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=max(120.0, result_cap))

    async def _send_turn_async(
        self,
        agent_id: str,
        user_text: str,
        *,
        deadline_monotonic: float,
        message_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        last_transport: BaseException | None = None
        for attempt in range(self._send_max_retries):
            await self._wait_online_async(deadline_monotonic=deadline_monotonic)
            if not self._ws or not self._response_q:
                last_transport = RuntimeError("websocket not connected")
                logger.warning("chat ws not connected before send (attempt {})", attempt)
                continue
            try:
                mid, payload = _ws_chat_turn_send_payload(agent_id, user_text, message_id)
                await self._ws.send(payload)
                while True:
                    data = await asyncio.wait_for(
                        self._response_q.get(), timeout=self._recv_timeout
                    )
                    try:
                        return _parse_chat_response_payload(data)
                    except ValueError as e:
                        logger.warning("chat ws skipped unexpected payload: {}", e)
            except ConnectionClosed as e:
                last_transport = e
                logger.info(
                    "chat ws ConnectionClosed during send_turn (attempt {})", attempt
                )
                continue
        if last_transport is not None:
            raise RuntimeError(
                f"chat ws send_turn failed after {self._send_max_retries} attempts"
            ) from last_transport
        raise RuntimeError(f"chat ws send_turn failed after {self._send_max_retries} attempts")


async def chat_turn_single_http_base(
    *,
    http_base: str,
    bearer_token: str,
    agent_id: str,
    user_text: str,
    connect_timeout: float = 30.0,
    # websockets 15+ defaults to proxy=True (read env). Use None to connect directly (e.g. localhost
    # without python-socks when ALL_PROXY is socks5://).
    proxy: str | Literal[True] | None = True,
) -> str:
    url = http_base_to_ws_chat_url(http_base)
    headers = [("Authorization", f"Bearer {bearer_token.strip()}")]
    recv_timeout = default_recv_timeout_sec()
    async with websockets.connect(
        url,
        additional_headers=headers,
        open_timeout=connect_timeout,
        ping_interval=None,
        proxy=proxy,
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
        text, _meta = _parse_chat_response_payload(data)
        return text
