"""WebSocket receive and assertions for companion interactive bootstrap kickoff."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import websockets

from tests.support.companion_ws_bootstrap.constants import (
    KICKOFF_MESSAGE_TYPE,
    WS_KEEPALIVE_PING_INTERVAL_SEC,
)
from tools.inty_v2_repl.backend_chat_ws import (
    BackendChatWsError,
    http_base_to_ws_chat_url,
    parse_chat_completion_ws_payload,
)


async def recv_first_chat_completion_frame(
    ws: Any,
    *,
    deadline_monotonic: float,
) -> dict[str, Any]:
    """Skip transport/control frames; return the first JSON object that carries ``code``."""
    while time.monotonic() < deadline_monotonic:
        remaining = max(0.05, deadline_monotonic - time.monotonic())
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"non-json ws frame (prefix): {raw[:400]!r}") from exc
        msg_type = data.get("type")
        if msg_type in ("pong", "client_context_ack", "user_signed_on_ack"):
            continue
        if "code" in data:
            return data
    raise TimeoutError("no chat completion JSON frame before deadline")


def assert_bootstrap_kickoff_payload(data: dict[str, Any], *, agent_id: str) -> None:
    try:
        content, meta = parse_chat_completion_ws_payload(data)
    except BackendChatWsError as exc:
        raise AssertionError(
            f"expected bootstrap kickoff (code 200), got ws error "
            f"code={exc.code} message={exc.agent_message!r} agent_id={exc.agent_id!r}"
        ) from exc
    mt = meta.get("messageType")
    assert mt == KICKOFF_MESSAGE_TYPE, (
        f"expected messageType={KICKOFF_MESSAGE_TYPE!r}, got {mt!r}, "
        f"code={data.get('code')}, meta_keys={sorted(meta.keys())}"
    )
    assert content.strip(), f"empty assistant content: {data!r}"
    aid = data.get("agent_id")
    assert aid == agent_id, f"agent_id mismatch: expected {agent_id!r}, got {aid!r}"


async def connect_and_expect_bootstrap_kickoff(
    *,
    http_base_url: str,
    bearer_token: str,
    agent_id: str,
    recv_timeout_sec: float,
) -> None:
    url = http_base_to_ws_chat_url(http_base_url, agent_id=agent_id)
    headers = [("Authorization", f"Bearer {bearer_token.strip()}")]
    deadline = time.monotonic() + recv_timeout_sec
    async with websockets.connect(
        url,
        additional_headers=headers,
        open_timeout=30,
        ping_interval=None,
    ) as ws:
        stop_ping = asyncio.Event()

        async def _keepalive_ping_loop() -> None:
            while not stop_ping.is_set():
                try:
                    await asyncio.wait_for(
                        stop_ping.wait(),
                        timeout=WS_KEEPALIVE_PING_INTERVAL_SEC,
                    )
                    return
                except asyncio.TimeoutError:
                    pass
                try:
                    await ws.send(json.dumps({"type": "ping"}))
                except Exception:
                    return

        ping_task = asyncio.create_task(_keepalive_ping_loop())
        try:
            frame = await recv_first_chat_completion_frame(
                ws, deadline_monotonic=deadline
            )
            assert_bootstrap_kickoff_payload(frame, agent_id=agent_id)
        finally:
            stop_ping.set()
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass
