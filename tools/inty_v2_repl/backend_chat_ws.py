"""WebSocket client for Inty ``/api/v1/chat/ws`` (transport only; companion runs on the server).

Wire payloads use types from ``app.schemas.chat`` (completion body) and
``app.schemas.chat_websocket`` (WebSocket envelope); downlink JSON parsing helpers live in this
module, not in ``app/schemas`` (schemas stay type-only).

Transport-only tunables (e.g. ``ws_conn_dropped`` / ``user_signed_out`` ack wait) use package-level
defaults here so the REPL does not import server ``config.yaml`` / ``app.core.config``.

On intentional shutdown (``BackendChatWsBridge.stop``), the client sends ``user_signed_out`` for the
URL ``agent_id`` before closing the socket so the server can reset companion scope like the mobile
app logout path.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from zoneinfo import ZoneInfo

import websockets
from websockets.exceptions import ConnectionClosed

from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
    CompanionChatTurnMessageType,
    UserTimeContext,
)
from app.schemas.chat_websocket import (
    ChatWebSocketRequest,
    normalize_websocket_companion_message_id_uuid,
)
from loguru import logger

# Seconds to wait for control-frame acks after sending ``ws_conn_dropped`` / ``user_signed_out``.
_WS_CONN_DROPPED_ACK_TIMEOUT_SEC: float = 5.0
_USER_SIGNED_OUT_ACK_TIMEOUT_SEC: float = 5.0


class BackendChatWsError(RuntimeError):
    def __init__(self, code: int, message: str, agent_id: str | None = None):
        self.code = code
        self.agent_message = message
        self.agent_id = agent_id
        super().__init__(f"chat ws error code={code} message={message!r}")


def default_ws_conn_dropped_ack_timeout_sec() -> float:
    return float(_WS_CONN_DROPPED_ACK_TIMEOUT_SEC)


def default_user_signed_out_ack_timeout_sec() -> float:
    return float(_USER_SIGNED_OUT_ACK_TIMEOUT_SEC)


def _ws_close_reason_text(reason: object | None) -> str:
    if reason is None:
        return ""
    if isinstance(reason, bytes):
        return reason.decode("utf-8", errors="replace")
    return str(reason)


def _ws_user_signed_on_json(agent_id: str, *, message_id: str) -> str:
    return json.dumps(
        {
            "type": "user_signed_on",
            "agent_id": agent_id.strip(),
            "message_id": message_id,
        }
    )


def _ws_user_signed_out_json(agent_id: str, *, message_id: str) -> str:
    return json.dumps(
        {
            "type": "user_signed_out",
            "agent_id": agent_id.strip(),
            "message_id": message_id,
        }
    )


def _ws_conn_dropped_json(
    agent_id: str,
    *,
    dropped_at_utc: str,
    message_id: str,
    ws_close_code: int | None,
    ws_close_reason: str,
) -> str:
    payload: dict[str, Any] = {
        "type": "ws_conn_dropped",
        "agent_id": agent_id.strip(),
        "dropped_at_utc": dropped_at_utc,
        "message_id": message_id,
    }
    if ws_close_code is not None:
        payload["ws_close_code"] = ws_close_code
    if ws_close_reason.strip():
        payload["ws_close_reason"] = ws_close_reason.strip()
    return json.dumps(payload)


def http_base_to_ws_chat_url(
    http_base: str,
    *,
    agent_id: str | None = None,
    ws_conn_id: str | None = None,
) -> str:
    base = http_base.strip().rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    url = f"{ws_base}/api/v1/chat/ws"
    params: list[tuple[str, str]] = []
    aid = (agent_id or "").strip()
    if aid:
        params.append(("agent_id", aid))
    wcid = (ws_conn_id or "").strip()
    if wcid:
        params.append(("ws_conn_id", wcid))
    if params:
        url = f"{url}?{urlencode(params)}"
    return url


def parse_chat_completion_ws_payload(
    data: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Parse one successful ``code==200`` chat completion JSON frame from ``/api/v1/chat/ws``."""
    return _parse_chat_response_payload(data)


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
        raise BackendChatWsError(
            int(code), msg, agent_id=str(aid) if aid is not None else None
        )
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


def _iana_tz_name_best_effort(now: datetime) -> str | None:
    """Resolve an IANA zone name when possible; macOS may lack a zoneinfo symlink."""
    tz_env = os.environ.get("TZ", "").strip()
    if tz_env:
        return tz_env
    zi = now.tzinfo
    if isinstance(zi, ZoneInfo):
        return zi.key
    try:
        localtime = Path("/etc/localtime")
        if localtime.is_symlink():
            parts = localtime.resolve().parts
            if "zoneinfo" in parts:
                i = parts.index("zoneinfo")
                tail = parts[i + 1 :]
                if tail:
                    return "/".join(tail)
    except OSError:
        pass
    return None


def build_ws_user_time_context_now() -> UserTimeContext:
    """Wall-clock context for ``time_context`` / ``client_context`` (local offset + optional IANA name)."""
    now = datetime.now().astimezone()
    off = now.utcoffset()
    utc_mins = int(off.total_seconds() // 60) if off is not None else None
    tz_name = _iana_tz_name_best_effort(now)
    return UserTimeContext(
        local_time=now.isoformat(timespec="milliseconds"),
        timezone=tz_name,
        utc_offset_minutes=utc_mins,
    )


def _ws_client_context_json() -> str:
    tc = build_ws_user_time_context_now()
    blob = tc.model_dump(by_alias=True, exclude_none=True)
    return json.dumps({"type": "client_context", "time_context": blob})


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
            user_time_context=build_ws_user_time_context_now(),
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

    def __init__(
        self,
        *,
        ws_url: str,
        bearer_token: str,
        on_user_signed_on_sent: Callable[[str, str], None] | None = None,
        on_user_signed_on_ack: Callable[[dict[str, Any]], None] | None = None,
        on_user_signed_out_sent: Callable[[str, str], None] | None = None,
        on_user_signed_out_ack: Callable[[dict[str, Any]], None] | None = None,
        on_transport_lost: Callable[[int | None, str], None] | None = None,
        on_transport_ready: Callable[[bool], None] | None = None,
    ) -> None:
        self._ws_url = ws_url
        self._bearer_token = bearer_token.strip()
        if not self._bearer_token:
            raise ValueError("bearer_token is empty")
        self._on_user_signed_on_sent = on_user_signed_on_sent
        self._on_user_signed_on_ack = on_user_signed_on_ack
        self._on_user_signed_out_sent = on_user_signed_out_sent
        self._on_user_signed_out_ack = on_user_signed_out_ack
        self._on_transport_lost = on_transport_lost
        self._on_transport_ready = on_transport_ready
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws: Any = None
        self._response_q: asyncio.Queue[dict[str, Any]] | None = None
        self._halt: asyncio.Event | None = None
        self._ready = threading.Event()
        self._start_error: Exception | None = None
        self._ping_interval = default_ping_interval_sec()
        self._recv_timeout = default_recv_timeout_sec()
        self._reconnect_initial = default_reconnect_initial_sec()
        self._reconnect_max = default_reconnect_max_sec()
        self._send_max_retries = default_send_turn_retries()
        self._online_ev: asyncio.Event | None = None
        self._had_transport_drop: bool = False
        self._pending_ws_drop: dict[str, Any] | None = None
        self._pending_ws_conn_dropped_ack_fut: asyncio.Future[dict[str, Any]] | None = (
            None
        )
        self._pending_user_signed_out_ack_fut: asyncio.Future[dict[str, Any]] | None = (
            None
        )

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
                loop.run_until_complete(
                    self._run_session(connect_timeout=connect_timeout)
                )
            except Exception as exc:
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
                    except Exception:
                        logger.exception("backend chat ws thread cleanup failed")
                    loop.close()
                self._loop = None
                self._ws = None
                self._ready.set()

        self._thread = threading.Thread(
            target=thread_main, name="inty-v2-chat-ws", daemon=True
        )
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
        frames or on **local parse failure** (so the REPL does not silently drop odd ``code==200`` payloads),
        ``(None, None, {})`` if the queue was empty.
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
            logger.exception("chat ws queued pop failed")
            return None, None, {}
        if raw is None:
            return None, None, {}
        try:
            text, meta = _parse_chat_response_payload(raw)
            return text, None, meta
        except BackendChatWsError as exc:
            return None, (int(exc.code), str(exc.agent_message)), {}
        except ValueError as exc:
            logger.warning("chat ws queued frame dropped: {}", raw)
            return (
                None,
                (
                    422,
                    f"Downlink chat JSON parse failed ({exc}). Check logs for raw frame.",
                ),
                {},
            )

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

    def _note_transport_drop(
        self,
        *,
        halt: asyncio.Event,
        code: int | None,
        reason: str,
    ) -> None:
        if halt.is_set():
            return
        self._pending_ws_drop = {
            "dropped_at_utc": datetime.now(timezone.utc).isoformat(),
            "ws_close_code": code,
            "ws_close_reason": reason,
        }
        self._had_transport_drop = True
        if self._on_transport_lost is not None:
            reason_note = reason if len(reason) <= 200 else reason[:200] + "…"
            try:
                self._on_transport_lost(code, reason_note)
            except Exception:
                logger.exception("on_transport_lost callback failed")

    async def _send_post_connect_control_frames(self, ws: Any) -> None:
        """After each successful connect: ``client_context``, optional ``ws_conn_dropped``, ``user_signed_on``."""
        reconnect = self._had_transport_drop
        if self._on_transport_ready is not None:
            try:
                self._on_transport_ready(reconnect)
            except Exception:
                logger.exception("on_transport_ready callback failed")
        if reconnect:
            self._had_transport_drop = False

        aid = _agent_id_from_ws_url(self._ws_url)
        if not aid:
            return

        try:
            await ws.send(_ws_client_context_json())
        except ConnectionClosed:
            logger.debug("chat ws client_context skipped (connection closed) agent_id={}", aid)
            return
        except Exception:
            logger.exception("chat ws client_context send failed agent_id={}", aid)

        pending_snapshot = self._pending_ws_drop
        self._pending_ws_drop = None

        if pending_snapshot:
            fut = asyncio.get_running_loop().create_future()
            self._pending_ws_conn_dropped_ack_fut = fut
            drop_mid = str(uuid.uuid4())
            try:
                await ws.send(
                    _ws_conn_dropped_json(
                        aid,
                        dropped_at_utc=str(pending_snapshot["dropped_at_utc"]),
                        message_id=drop_mid,
                        ws_close_code=pending_snapshot.get("ws_close_code"),
                        ws_close_reason=str(
                            pending_snapshot.get("ws_close_reason") or ""
                        ),
                    )
                )
                try:
                    ack = await asyncio.wait_for(
                        fut, timeout=default_ws_conn_dropped_ack_timeout_sec()
                    )
                except TimeoutError:
                    logger.warning(
                        "chat ws ws_conn_dropped_ack timed out agent_id={}",
                        aid,
                    )
                else:
                    if isinstance(ack, dict) and ack.get("ok") is False:
                        logger.warning(
                            "chat ws ws_conn_dropped_ack ok=false agent_id={} ack={}",
                            aid,
                            ack,
                        )
            except ConnectionClosed:
                logger.debug(
                    "chat ws ws_conn_dropped skipped (connection closed) agent_id={}",
                    aid,
                )
                self._pending_ws_conn_dropped_ack_fut = None
                return
            finally:
                self._pending_ws_conn_dropped_ack_fut = None

        try:
            frame_mid = str(uuid.uuid4())
            await ws.send(
                _ws_user_signed_on_json(aid, message_id=frame_mid),
            )
            logger.info(
                "chat ws user_signed_on sent (repl) agent_id={} message_id={}",
                aid,
                frame_mid,
            )
            if self._on_user_signed_on_sent is not None:
                try:
                    self._on_user_signed_on_sent(aid, frame_mid)
                except Exception:
                    logger.exception("on_user_signed_on_sent callback failed")
        except ConnectionClosed:
            logger.debug("chat ws user_signed_on skipped (connection closed)")
        except Exception:
            logger.exception("chat ws user_signed_on send failed agent_id={}", aid)

    async def _send_user_signed_out_before_shutdown(self, ws: Any) -> None:
        """Best-effort ``user_signed_out`` so server resets companion scope before socket close."""
        aid = _agent_id_from_ws_url(self._ws_url)
        if not aid:
            return
        fut = asyncio.get_running_loop().create_future()
        self._pending_user_signed_out_ack_fut = fut
        frame_mid = str(uuid.uuid4())
        try:
            await ws.send(_ws_user_signed_out_json(aid, message_id=frame_mid))
            logger.info(
                "chat ws user_signed_out sent (repl shutdown) agent_id={} message_id={}",
                aid,
                frame_mid,
            )
            if self._on_user_signed_out_sent is not None:
                try:
                    self._on_user_signed_out_sent(aid, frame_mid)
                except Exception:
                    logger.exception("on_user_signed_out_sent callback failed")
            try:
                ack = await asyncio.wait_for(
                    fut, timeout=default_user_signed_out_ack_timeout_sec()
                )
            except TimeoutError:
                logger.warning(
                    "chat ws user_signed_out_ack timed out agent_id={}",
                    aid,
                )
            else:
                if isinstance(ack, dict) and ack.get("ok") is False:
                    logger.warning(
                        "chat ws user_signed_out_ack ok=false agent_id={} ack={}",
                        aid,
                        ack,
                    )
                if self._on_user_signed_out_ack is not None:
                    try:
                        self._on_user_signed_out_ack(ack)
                    except Exception:
                        logger.exception("on_user_signed_out_ack callback failed")
        except ConnectionClosed:
            logger.debug(
                "chat ws user_signed_out skipped (connection closed) agent_id={}",
                aid,
            )
        except Exception:
            logger.exception(
                "chat ws user_signed_out send failed agent_id={}",
                aid,
            )
        finally:
            self._pending_user_signed_out_ack_fut = None

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
                except Exception as exc:
                    if not self._ready.is_set():
                        raise RuntimeError(
                            f"initial WebSocket connect failed: {exc}"
                        ) from exc
                    logger.warning("chat ws reconnect connect failed: {}", exc)
                    await self._sleep_backoff(reconnect_idx, halt)
                    reconnect_idx += 1
                    continue
                self._ws = ws
                self._response_q = asyncio.Queue()
                self._online_ev.set()
                reconnect_idx = 0
                reader_task = asyncio.create_task(self._read_loop(ws, halt))
                await asyncio.sleep(0)
                await self._send_post_connect_control_frames(ws)
                if not self._ready.is_set():
                    self._ready.set()
                pinger = asyncio.create_task(self._pinger_loop(ws, halt))
                halt_task = asyncio.create_task(halt.wait())
                try:
                    _done, pending = await asyncio.wait(
                        {reader_task, halt_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if halt.is_set():
                        # Reader must stay alive until user_signed_out_ack is consumed.
                        if halt_task in pending:
                            halt_task.cancel()
                            await asyncio.gather(halt_task, return_exceptions=True)
                    else:
                        for t in pending:
                            t.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                finally:
                    pinger.cancel()
                    try:
                        await pinger
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        logger.exception("pinger task exit")
                if halt.is_set():
                    await self._send_user_signed_out_before_shutdown(ws)
                    reader_task.cancel()
                    try:
                        await reader_task
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        logger.exception("reader task exit")
                    try:
                        await ws.close()
                    except Exception:
                        logger.exception("chat ws close failed during halt")
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
                    except Exception:
                        logger.exception("reader task exit")
                logger.info("chat ws read loop ended; reconnecting")
                try:
                    await ws.close()
                except Exception:
                    logger.exception("chat ws close failed before reconnect")
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

    async def _read_loop(self, ws: Any, halt: asyncio.Event) -> None:
        if self._response_q is None:
            raise RuntimeError("response queue not initialized")
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
                if data.get("type") == "ws_conn_dropped_ack":
                    fut = self._pending_ws_conn_dropped_ack_fut
                    if fut is not None and not fut.done():
                        fut.set_result(data)
                    continue
                if data.get("type") == "user_signed_on_ack":
                    if self._on_user_signed_on_ack is not None:
                        try:
                            self._on_user_signed_on_ack(data)
                        except Exception:
                            logger.exception("on_user_signed_on_ack callback failed")
                    continue
                if data.get("type") == "user_signed_out_ack":
                    fut = self._pending_user_signed_out_ack_fut
                    if fut is not None and not fut.done():
                        fut.set_result(data)
                    elif self._on_user_signed_out_ack is not None:
                        try:
                            self._on_user_signed_out_ack(data)
                        except Exception:
                            logger.exception("on_user_signed_out_ack callback failed")
                    continue
                if "code" in data:
                    await self._response_q.put(data)
                    continue
                logger.warning(
                    "chat ws unexpected json keys={}", list(data.keys())[:12]
                )
        except ConnectionClosed as e:
            logger.info("chat ws read loop closed: {}", e)
            rcvd = e.rcvd
            self._note_transport_drop(
                halt=halt,
                code=rcvd.code if rcvd is not None else None,
                reason=_ws_close_reason_text(rcvd.reason if rcvd is not None else None),
            )
        except asyncio.CancelledError:
            raise
        else:
            if not halt.is_set():
                self._note_transport_drop(halt=halt, code=None, reason="")

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
        if (
            self._loop is not None
            and self._loop.is_running()
            and self._halt is not None
        ):
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
        last_transport: Exception | None = None
        for attempt in range(self._send_max_retries):
            await self._wait_online_async(deadline_monotonic=deadline_monotonic)
            if not self._ws or not self._response_q:
                last_transport = RuntimeError("websocket not connected")
                logger.warning(
                    "chat ws not connected before post_turn (attempt {})", attempt
                )
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
        raise RuntimeError(
            f"chat ws post_turn failed after {self._send_max_retries} attempts"
        )

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
