"""Minimal WeChat (Hermes WeixinAdapter) -> Inty companion WebSocket bridge."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from urllib.parse import urlencode

import websockets
from gateway.config import PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.platforms.weixin import WeixinAdapter


def _http_base_to_ws_chat_url(http_base: str, ws_conn_id: str) -> str:
    base = http_base.strip().rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_base}/api/v1/chat/ws?{urlencode({'ws_conn_id': ws_conn_id})}"


def _client_context_frame() -> str:
    now = datetime.now().astimezone()
    off = now.utcoffset()
    return json.dumps(
        {
            "type": "client_context",
            "time_context": {
                "local_time": now.isoformat(timespec="milliseconds"),
                "timezone": os.environ.get("TZ") or None,
                "utc_offset_minutes": int(off.total_seconds() // 60) if off else None,
            },
        }
    )


def _chat_turn_frame(agent_id: str, user_text: str, message_id: str) -> str:
    return json.dumps(
        {
            "agent_id": agent_id,
            "request": {
                "messages": [{"role": "user", "content": user_text}],
                "message_id": message_id,
            },
        }
    )


async def ask_inty(user_text: str) -> str:
    ws_url = _http_base_to_ws_chat_url(
        os.environ["INTY_API_BASE_URL"],
        str(uuid.uuid4()),
    )
    headers = [("Authorization", f"Bearer {os.environ['INTY_JWT']}")]
    agent_id = os.environ["INTY_AGENT_ID"]

    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        await ws.send(_client_context_frame())
        await ws.send(
            _chat_turn_frame(agent_id, user_text, str(uuid.uuid4())),
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


async def handle_weixin_message(event: MessageEvent) -> str:
    return await ask_inty(event.text)


async def main() -> None:
    config = PlatformConfig(
        enabled=True,
        token=os.environ["WEIXIN_TOKEN"],
        extra={
            "account_id": os.environ["WEIXIN_ACCOUNT_ID"],
            "base_url": os.getenv(
                "WEIXIN_BASE_URL",
                "https://ilinkai.weixin.qq.com",
            ),
            "dm_policy": "open",
            "group_policy": "disabled",
        },
    )
    adapter = WeixinAdapter(config)
    adapter.set_message_handler(handle_weixin_message)
    await adapter.connect()
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
