"""TelegramTransport routes inbound text by telegram chat_id."""

from __future__ import annotations

import json
import time
from io import BytesIO
from urllib.error import HTTPError

import pytest

from app.db.session import async_engine
from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    TelegramIncomingMessage,
)
from app.models.registry import load_model_modules
from backend.ops.telegram_demo import session_store
from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo.session_store import clear_all_for_tests
from backend.ops.telegram_demo.transport import TelegramTransport


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _fake_urlopen(request, timeout=15):
    url = request.full_url
    if url.endswith("/getMe"):
        return _FakeResponse(
            {
                "ok": True,
                "result": {"id": 42, "username": "demo_bot"},
            }
        )
    if "/getUpdates" in url:
        return _FakeResponse({"ok": True, "result": []})
    if url.endswith("/sendMessage"):
        return _FakeResponse({"ok": True, "result": {}})
    raise HTTPError(url, 404, "not found", hdrs=None, fp=BytesIO())


@pytest.fixture(autouse=True)
async def _reset_transport_store() -> None:
    clear_all_for_tests()
    yield
    clear_all_for_tests()
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_handle_inbound_routes_text_to_binding_chat_id() -> None:
    """Uses real ``get_or_create_presence``; fails fast when Inty user row is missing."""
    load_model_modules()
    await async_engine.dispose()
    telegram_chat_id = "5078060274"
    binding = TelegramDemoBinding(
        telegram_chat_id=telegram_chat_id,
        user_id="missing-user-id",
        agent_id="missing-agent-id",
        chat_id="missing-chat-id",
    )
    session_store._bindings_by_chat_id[binding.telegram_chat_id] = binding

    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)
    inbound = TelegramIncomingMessage(
        update_id=1,
        chat_id=telegram_chat_id,
        text="你好",
        local_received_at=time.time(),
    )
    reply = await transport._handle_inbound(inbound)

    assert reply == "无法找到你的 Inty 用户，请重新 /start。"


@pytest.mark.asyncio
async def test_handle_inbound_unknown_chat_prompts_onboard() -> None:
    api = TelegramBotApi(bot_token="route-test-token", urlopen=_fake_urlopen)
    transport = TelegramTransport(api=api)
    inbound = TelegramIncomingMessage(
        update_id=2,
        chat_id="999",
        text="hello",
        local_received_at=time.time(),
    )
    reply = await transport._handle_inbound(inbound)
    assert "onboard" in reply
