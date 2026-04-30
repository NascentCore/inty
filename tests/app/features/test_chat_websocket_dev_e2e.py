"""
Chat WebSocket E2E against a running backend using real LLM.

Enable with INTY_CHAT_WS_REAL_TEST=1. Set INTY_DEV_CONFIG_PATH to the YAML the
server uses (e.g. devops/config.yaml.dev or devops/config.yaml.local); tests
require app.environment in {"dev", "local"}.

Does not run in default CI (noci + env gate).
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path

import pytest
import yaml

from tests.app.api.test_client import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DEV_CONFIG = REPO_ROOT / "devops" / "config.yaml.dev"
API_BASE_URL = os.getenv("INTY_API_BASE_URL", "http://localhost:8000")


def _require_real_ws_test() -> None:
    if os.getenv("INTY_CHAT_WS_REAL_TEST") != "1":
        pytest.skip("Set INTY_CHAT_WS_REAL_TEST=1 to run chat WebSocket real LLM tests")


_ALLOWED_REAL_WS_ENVIRONMENTS = frozenset({"dev", "local"})


def _load_operator_config_assert_real_backend() -> dict:
    path = os.getenv("INTY_DEV_CONFIG_PATH", str(DEFAULT_DEV_CONFIG))
    cfg_path = Path(path)
    if not cfg_path.is_file():
        pytest.skip(f"Operator config not found: {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    env = (data.get("app") or {}).get("environment")
    if env not in _ALLOWED_REAL_WS_ENVIRONMENTS:
        pytest.skip(
            f"INTY_DEV_CONFIG_PATH must have app.environment in {_ALLOWED_REAL_WS_ENVIRONMENTS!r}, got {env!r}"
        )
    return data


def _http_to_ws_base(http_base: str) -> str:
    return http_base.replace("http://", "ws://").replace("https://", "wss://").rstrip(
        "/"
    )


@pytest.fixture
def integration_client():
    _require_real_ws_test()
    _load_operator_config_assert_real_backend()
    client = TestClient(API_BASE_URL)
    client.create_user()
    try:
        yield client
    finally:
        client.delete_user()
        client.close()


@pytest.mark.noci
@pytest.mark.slow
@pytest.mark.asyncio
async def test_chat_websocket_dev_ping_pong(integration_client: TestClient):
    import websockets

    token = integration_client.token
    assert token
    ws_base = _http_to_ws_base(API_BASE_URL)
    url = f"{ws_base}/api/v1/chat/ws"
    headers = [("Authorization", f"Bearer {token}")]
    async with websockets.connect(
        url,
        additional_headers=headers,
        open_timeout=30,
        ping_interval=None,
    ) as ws:
        await ws.send(json.dumps({"type": "ping"}))
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        body = json.loads(raw)
        assert body.get("type") == "pong"


@pytest.mark.noci
@pytest.mark.slow
@pytest.mark.asyncio
async def test_chat_websocket_dev_real_llm_roundtrip(integration_client: TestClient):
    import websockets
    from websockets.exceptions import InvalidStatus

    agent_id = integration_client.create_agent(
        name="WS dev e2e agent",
        personality="Brief replies for integration testing.",
    )
    token = integration_client.token
    ws_base = _http_to_ws_base(API_BASE_URL)
    url = f"{ws_base}/api/v1/chat/ws"
    headers = [("Authorization", f"Bearer {token}")]
    payload = {
        "agent_id": agent_id,
        "request": {
            "messages": [
                {
                    "role": "user",
                    "content": 'Reply with exactly the word "pong" and nothing else.',
                }
            ],
            "stream": False,
            "model": "chatbot",
            "message_id": str(uuid.uuid4()),
        },
    }
    recv_timeout = float(os.getenv("INTY_CHAT_WS_RECV_TIMEOUT", "120"))
    try:
        async with websockets.connect(
            url,
            additional_headers=headers,
            open_timeout=30,
            ping_interval=None,
        ) as ws:
            await ws.send(json.dumps(payload))
            raw = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
    except InvalidStatus as e:
        pytest.fail(f"WebSocket handshake failed: {e}")

    data = json.loads(raw)
    assert data.get("code") == 200, data
    assert data.get("agent_id") == agent_id
    inner = data.get("data") or {}
    choices = inner.get("choices") or []
    assert len(choices) >= 1
    msg = (choices[0].get("message") or {})
    content = msg.get("content")
    assert isinstance(content, str)
    assert len(content.strip()) > 0


@pytest.mark.noci
@pytest.mark.slow
@pytest.mark.asyncio
async def test_chat_websocket_dev_unauthorized_close_code():
    import websockets
    from websockets.exceptions import ConnectionClosedError

    _require_real_ws_test()
    _load_operator_config_assert_real_backend()
    ws_base = _http_to_ws_base(API_BASE_URL)
    url = f"{ws_base}/api/v1/chat/ws"
    with pytest.raises(ConnectionClosedError) as excinfo:
        async with websockets.connect(url, open_timeout=30, ping_interval=None) as ws:
            await asyncio.wait_for(ws.recv(), timeout=10)
    assert excinfo.value.rcvd is not None
    assert excinfo.value.rcvd.code == 4001
