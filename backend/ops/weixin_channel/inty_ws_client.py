"""Long-lived Inty ``/api/v1/chat/ws`` client for Ops Weixin channel.

TODO(wechat-demo-ws-disconnect-hermes-wording): no auto-reconnect. Inty backend restart
closes this WS with 1012 (service restart); ``send_user_text`` / read_loop raise
``ConnectionClosed*``, then Hermes WeixinAdapter sends misleading "/reset" copy to the
peer. Reconnect via ``WeixinChannelSession.start`` or wechat-demo bridge restore.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from urllib.parse import urlencode

import websockets
from loguru import logger
from pydantic import ValidationError
from websockets.exceptions import ConnectionClosed

from app.schemas.chat import ChatCompletionRequest, ChatMessage, UserTimeContext
from app.schemas.chat_websocket import (
    ChatWebSocketRequest,
    ChatWebSocketResponse,
    ChatWsClientContextAckFrame,
    ChatWsClientContextFrame,
    ChatWsCompanionWireMessageMetaData,
    ChatWsPingFrame,
    ChatWsPongFrame,
    ChatWsUserSignedOnAckFrame,
    ChatWsUserSignedOnFrame,
    ChatWsUserSignedOutFrame,
    normalize_websocket_companion_message_id_uuid,
)

ProactivePushHandler = Callable[[str], Awaitable[None]]

# Below server ``chat_ws_idle_timeout_seconds`` minimum (10s); matches iMate Android.
_WS_PING_INTERVAL_SEC = 9.0
_SEND_ATTEMPT_COUNT = 2
_WS_NORMAL_CLOSE_MESSAGE = "Inty WebSocket closed normally"


class IntyWsChannelState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    FAILED = "failed"


class IntyWsChannelClosed(RuntimeError):
    """Raised for a closed Inty WS when no protocol close exception is available."""


@dataclass(frozen=True)
class IntyWsChannelConfig:
    """Parameters for one companion WebSocket session."""

    api_base_url: str
    jwt: str
    agent_id: str


def http_base_to_ws_chat_url(http_base: str, ws_conn_id: str) -> str:
    base = http_base.rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_base}/api/v1/chat/ws?{urlencode({'ws_conn_id': ws_conn_id})}"


def _assistant_text_from_response_payload(raw: dict[str, Any]) -> str | None:
    try:
        frame = ChatWebSocketResponse.model_validate(raw)
    except ValidationError:
        return None
    if frame.code != 200:
        return None
    data = frame.data
    if not isinstance(data, dict):
        return None
    choices = data.get("choices") or []
    if not choices:
        return None
    msg0 = (choices[0] or {}).get("message") or {}
    content = msg0.get("content")
    if content is None:
        return None
    return str(content)


def _message_meta_from_response_payload(
    raw: dict[str, Any],
) -> ChatWsCompanionWireMessageMetaData | None:
    # TODO(issue#3207): parse success frames via ChatWebSocketQueuedSuccessFrame.
    try:
        frame = ChatWebSocketResponse.model_validate(raw)
    except ValidationError:
        return None
    if frame.code != 200 or not isinstance(frame.data, dict):
        return None
    choices = frame.data.get("choices") or []
    if not choices:
        return None
    msg0 = (choices[0] or {}).get("message") or {}
    meta_raw = msg0.get("meta_data") or msg0.get("metaData")
    if not isinstance(meta_raw, dict):
        return None
    try:
        return ChatWsCompanionWireMessageMetaData.model_validate(meta_raw)
    except ValidationError:
        return None


def is_proactive_chat_downlink(
    meta: ChatWsCompanionWireMessageMetaData | None,
) -> bool:
    if meta is None:
        return False
    if meta.companion_proactive_chat is True or meta.proactive_chat is True:
        return True
    activity = meta.inner_tick_activity
    return activity == "proactive_chat"


class IntyWsChannelClient:
    """One long-lived WS to Inty; arms inner-tick via ``user_signed_on``."""

    def __init__(
        self,
        config: IntyWsChannelConfig,
        on_proactive_push: ProactivePushHandler,
        timezone_name: str | None,
    ) -> None:
        assert config.api_base_url != ""
        assert config.jwt != ""
        assert config.agent_id != ""
        self._config = config
        self._on_proactive_push = on_proactive_push
        self._timezone_name = timezone_name
        self._ws: websockets.ClientConnection | None = None
        self._read_task: asyncio.Task[None] | None = None
        self._ping_task: asyncio.Task[None] | None = None
        self._state = IntyWsChannelState.DISCONNECTED
        self._pending_replies: asyncio.Queue[asyncio.Future[str]] = (
            asyncio.Queue()
        )
        self._signed_on = False
        self._ws_conn_id = str(uuid.uuid4())

    @property
    def state(self) -> IntyWsChannelState:
        return self._state

    @property
    def signed_on(self) -> bool:
        return self._signed_on

    async def connect(self) -> None:
        if self._state == IntyWsChannelState.READY:
            return
        await self._cancel_background_task(self._ping_task)
        self._ping_task = None
        if self._read_task is not None and self._read_task is not asyncio.current_task():
            await self._cancel_background_task(self._read_task)
        self._read_task = None
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                logger.debug(
                    "inty_ws_channel stale close failed ws_conn_id={}",
                    self._ws_conn_id,
                )
        self._ws = None
        self._signed_on = False
        self._ws_conn_id = str(uuid.uuid4())
        self._state = IntyWsChannelState.CONNECTING
        ws_url = http_base_to_ws_chat_url(
            self._config.api_base_url,
            self._ws_conn_id,
        )
        headers = [("Authorization", f"Bearer {self._config.jwt}")]
        self._ws = await websockets.connect(ws_url, additional_headers=headers)
        await self._send_client_context()
        await self._send_user_signed_on()
        self._read_task = asyncio.create_task(
            self._read_loop(),
            name=f"inty_ws_channel_read_{self._ws_conn_id}",
        )
        self._ping_task = asyncio.create_task(
            self._pinger_loop(),
            name=f"inty_ws_channel_ping_{self._ws_conn_id}",
        )
        self._state = IntyWsChannelState.READY

    def _fail_pending_replies(self, exc: BaseException) -> None:
        while not self._pending_replies.empty():
            fut = self._pending_replies.get_nowait()
            if not fut.done():
                fut.set_exception(exc)

    async def _cancel_background_task(
        self, task: asyncio.Task[None] | None
    ) -> None:
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def disconnect(self) -> None:
        await self._cancel_background_task(self._ping_task)
        self._ping_task = None
        await self._cancel_background_task(self._read_task)
        self._read_task = None
        ws = self._ws
        if ws is not None and self._signed_on:
            try:
                frame = ChatWsUserSignedOutFrame(
                    agent_id=self._config.agent_id,
                    message_id=str(uuid.uuid4()),
                )
                await ws.send(frame.model_dump_json())
            except Exception:
                logger.debug(
                    "inty_ws_channel user_signed_out send failed ws_conn_id={}",
                    self._ws_conn_id,
                )
        if ws is not None:
            await ws.close()
        self._ws = None
        self._signed_on = False
        self._state = IntyWsChannelState.DISCONNECTED
        while not self._pending_replies.empty():
            fut = self._pending_replies.get_nowait()
            if not fut.done():
                fut.set_exception(asyncio.CancelledError())

    async def send_user_text(self, user_text: str) -> str:
        assert user_text != ""
        last_closed: BaseException | None = None
        for _attempt in range(_SEND_ATTEMPT_COUNT):
            if (
                self._state != IntyWsChannelState.READY
                or self._ws is None
                or not self._signed_on
            ):
                await self.connect()
            assert self._ws is not None
            assert self._signed_on
            message_id = str(uuid.uuid4())
            request = ChatWebSocketRequest(
                agent_id=self._config.agent_id,
                request=ChatCompletionRequest(
                    messages=[ChatMessage(role="user", content=user_text)],
                    message_id=message_id,
                ),
            )
            reply_fut: asyncio.Future[str] = (
                asyncio.get_running_loop().create_future()
            )
            await self._pending_replies.put(reply_fut)
            try:
                await self._ws.send(request.model_dump_json())
                return await reply_fut
            except ConnectionClosed as exc:
                last_closed = exc
                self._state = IntyWsChannelState.FAILED
                self._signed_on = False
                self._fail_pending_replies(exc)
                logger.info(
                    "inty_ws_channel send closed retrying ws_conn_id={}: {}",
                    self._ws_conn_id,
                    exc,
                )
        if last_closed is not None:
            raise last_closed
        raise IntyWsChannelClosed(_WS_NORMAL_CLOSE_MESSAGE)

    async def _send_client_context(self) -> None:
        assert self._ws is not None
        now = datetime.now().astimezone()
        off = now.utcoffset()
        utc_offset_minutes = (
            int(off.total_seconds() // 60) if off is not None else None
        )
        frame = ChatWsClientContextFrame(
            time_context=UserTimeContext(
                local_time=now.isoformat(timespec="milliseconds"),
                timezone=self._timezone_name,
                utc_offset_minutes=utc_offset_minutes,
            ),
        )
        await self._ws.send(frame.model_dump_json())
        raw = await self._ws.recv()
        data = json.loads(raw)
        ack = ChatWsClientContextAckFrame.model_validate(data)
        if not ack.ok:
            raise RuntimeError("client_context rejected")

    async def _send_user_signed_on(self) -> None:
        assert self._ws is not None
        signed_on_id = normalize_websocket_companion_message_id_uuid(
            str(uuid.uuid4())
        )
        frame = ChatWsUserSignedOnFrame(
            agent_id=self._config.agent_id,
            message_id=signed_on_id,
        )
        await self._ws.send(frame.model_dump_json())
        raw = await self._ws.recv()
        data = json.loads(raw)
        ack = ChatWsUserSignedOnAckFrame.model_validate(data)
        if not ack.ok:
            reason = ack.reason or "unknown"
            raise RuntimeError(f"user_signed_on rejected: {reason}")
        self._signed_on = True

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                await self._handle_raw_frame(str(raw))
        except asyncio.CancelledError:
            raise
        except ConnectionClosed as exc:
            # TODO(wechat-demo-ws-disconnect-hermes-wording): 1012 = Inty uvicorn shutdown;
            # pending DM replies fail; user may see Hermes "/reset" text, not Inty-owned.
            logger.info(
                "inty_ws_channel read_loop closed ws_conn_id={}: {}",
                self._ws_conn_id,
                exc,
            )
            self._state = IntyWsChannelState.FAILED
            self._signed_on = False
            self._fail_pending_replies(exc)
        except Exception as exc:
            logger.exception(
                "inty_ws_channel read_loop failed ws_conn_id={}: {}",
                self._ws_conn_id,
                exc,
            )
            self._state = IntyWsChannelState.FAILED
            self._signed_on = False
            self._fail_pending_replies(exc)
        else:
            exc = IntyWsChannelClosed(_WS_NORMAL_CLOSE_MESSAGE)
            logger.info(
                "inty_ws_channel read_loop ended ws_conn_id={}: {}",
                self._ws_conn_id,
                exc,
            )
            self._state = IntyWsChannelState.FAILED
            self._signed_on = False
            self._fail_pending_replies(exc)

    async def _pinger_loop(self) -> None:
        assert self._ws is not None
        ping_payload = ChatWsPingFrame().model_dump_json()
        try:
            while True:
                await asyncio.sleep(_WS_PING_INTERVAL_SEC)
                try:
                    await self._ws.send(ping_payload)
                except ConnectionClosed:
                    return
        except asyncio.CancelledError:
            raise

    async def _handle_raw_frame(self, raw: str) -> None:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return
        msg_type = data.get("type")
        match msg_type:
            case "pong":
                ChatWsPongFrame.model_validate(data)
                return
            case (
                "client_context_ack"
                | "user_signed_on_ack"
                | "user_signed_out_ack"
            ):
                return
            case _:
                pass

        text = _assistant_text_from_response_payload(data)
        if text is None:
            return
        meta = _message_meta_from_response_payload(data)
        if is_proactive_chat_downlink(meta):
            stripped = text.strip()
            if stripped:
                await self._on_proactive_push(stripped)
            return

        if not self._pending_replies.empty():
            fut = self._pending_replies.get_nowait()
            if not fut.done():
                fut.set_result(text)
