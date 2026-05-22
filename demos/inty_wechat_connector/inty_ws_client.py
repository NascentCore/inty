"""Inty companion chat WebSocket client helpers for the WeChat connector demo."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

import websockets


@dataclass(frozen=True)
class IntyWsConnection:
    """Parameters for one Inty ``/api/v1/chat/ws`` turn."""

    api_base_url: str
    jwt: str
    agent_id: str


def http_base_to_ws_chat_url(http_base: str, ws_conn_id: str) -> str:
    base = http_base.strip().rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_base}/api/v1/chat/ws?{urlencode({'ws_conn_id': ws_conn_id})}"


def client_context_frame(timezone_name: str | None) -> str:
    now = datetime.now().astimezone()
    off = now.utcoffset()
    return json.dumps(
        {
            "type": "client_context",
            "time_context": {
                "local_time": now.isoformat(timespec="milliseconds"),
                "timezone": timezone_name,
                "utc_offset_minutes": int(off.total_seconds() // 60) if off else None,
            },
        }
    )


def chat_turn_frame(agent_id: str, user_text: str, message_id: str) -> str:
    return json.dumps(
        {
            "agent_id": agent_id,
            "request": {
                "messages": [{"role": "user", "content": user_text}],
                "message_id": message_id,
            },
        }
    )


async def ask_inty(user_text: str, conn: IntyWsConnection) -> str:
    assert conn.api_base_url.strip() != ""
    assert conn.jwt.strip() != ""
    assert conn.agent_id.strip() != ""
    assert user_text != ""

    ws_url = http_base_to_ws_chat_url(conn.api_base_url, str(uuid.uuid4()))
    headers = [("Authorization", f"Bearer {conn.jwt}")]

    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        await ws.send(client_context_frame(os.environ.get("TZ")))
        await ws.send(
            chat_turn_frame(conn.agent_id, user_text, str(uuid.uuid4())),
        )
        async for raw in ws:
            data = json.loads(raw)
            if data.get("type") in ("pong", "client_context_ack"):
                continue
            if data.get("code") != 200:
                continue
            inner = data["data"] or {}
            choices = inner.get("choices") or []
            msg0 = (choices[0] or {}).get("message") or {}
            return str(msg0.get("content") or "")

    return ""
