"""Pure helpers for ``/api/v1/chat/ws`` response parsing (no loopback client)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from pydantic import ValidationError

from app.schemas.chat_websocket import (
    ChatWebSocketResponse,
    ChatWsCompanionWireMessageMetaData,
)

# Documented alongside iMate Android; below server ``chat_ws_idle_timeout_seconds`` minimum (10s).
CHAT_WS_CLIENT_PING_INTERVAL_SEC = 9.0


def http_base_to_ws_chat_url(http_base: str, ws_conn_id: str) -> str:
    base = http_base.rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_base}/api/v1/chat/ws?{urlencode({'ws_conn_id': ws_conn_id})}"


def assistant_text_from_response_payload(raw: dict[str, Any]) -> str | None:
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


def is_proactive_chat_downlink(
    meta: ChatWsCompanionWireMessageMetaData | None,
) -> bool:
    if meta is None:
        return False
    if meta.companion_proactive_chat is True or meta.proactive_chat is True:
        return True
    activity = meta.inner_tick_activity
    return activity == "proactive_chat"
