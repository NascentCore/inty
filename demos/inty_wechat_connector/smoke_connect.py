"""Verify Inty WebSocket accepts client_context (transport only)."""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import websockets

from bridge import _client_context_frame, _http_base_to_ws_chat_url


async def main() -> None:
    ws_url = _http_base_to_ws_chat_url(
        os.environ["INTY_API_BASE_URL"],
        str(uuid.uuid4()),
    )
    headers = [("Authorization", f"Bearer {os.environ['INTY_JWT']}")]
    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        await ws.send(_client_context_frame())
        raw = await ws.recv()
        data = json.loads(raw)
        assert data.get("type") == "client_context_ack" and data.get("ok") is True
        print("smoke_connect ok:", data)


if __name__ == "__main__":
    asyncio.run(main())
