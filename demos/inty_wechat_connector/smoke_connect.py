"""Verify Inty WebSocket accepts client_context (transport only)."""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import websockets

from demos.inty_wechat_connector.inty_ws_client import (
    client_context_frame,
    http_base_to_ws_chat_url,
)


async def main() -> None:
    ws_url = http_base_to_ws_chat_url(
        os.environ["INTY_API_BASE_URL"],
        str(uuid.uuid4()),
    )
    headers = [("Authorization", f"Bearer {os.environ['INTY_JWT']}")]
    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        await ws.send(client_context_frame(os.environ.get("TZ")))
        raw = await ws.recv()
        data = json.loads(raw)
        assert data.get("type") == "client_context_ack" and data.get("ok") is True
        print("smoke_connect ok:", data)


if __name__ == "__main__":
    asyncio.run(main())
