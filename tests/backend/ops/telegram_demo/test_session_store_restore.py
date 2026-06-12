"""Integration tests for telegram-demo session restore and presence lifecycle."""

from __future__ import annotations

import json
import uuid
from io import BytesIO
from urllib.error import HTTPError

import pytest
from sqlalchemy import delete

from app.db.session import AsyncSessionLocal, async_engine
from app.external_services.telegram_bot_api import TelegramBotApi
from app.models.chat import Chat
from app.models.ops_telegram_demo import OpsTelegramDemoBinding
from app.models.registry import load_model_modules
from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo.persistence import delete_binding, upsert_binding
from backend.ops.telegram_demo.provision import provision_inty_for_telegram_onboard
from backend.ops.telegram_demo import session_store
from backend.ops.telegram_demo.session_store import (
    clear_all_for_tests,
    get_binding,
    get_or_create_presence,
    restore_persisted_bindings,
    start_presence,
    stop_all_presences,
)


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


def _telegram_api() -> TelegramBotApi:
    return TelegramBotApi(bot_token="restore-test-token", urlopen=_fake_urlopen)


async def _cleanup_provision(telegram_chat_id: str, user_id: str) -> None:
    await delete_binding(telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Chat).where(Chat.user_id == user_id))
        await db.execute(
            delete(OpsTelegramDemoBinding).where(
                OpsTelegramDemoBinding.telegram_chat_id == telegram_chat_id
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_session_store_restore_scenarios() -> None:
    """Single async test: shared ``async_engine`` pool breaks across loop-bound tests."""
    load_model_modules()
    await async_engine.dispose()
    clear_all_for_tests()

    telegram_chat_id = f"tg-restore-{uuid.uuid4().hex}"
    provision = await provision_inty_for_telegram_onboard(
        telegram_chat_id=telegram_chat_id,
    )
    binding = TelegramDemoBinding(
        telegram_chat_id=telegram_chat_id,
        user_id=provision.user_id,
        agent_id=provision.agent_id,
        chat_id=provision.chat_id,
    )
    try:
        started = await start_presence(binding, api=_telegram_api())
        assert started._presence is not None
        await stop_all_presences()

        session_store._bindings_by_chat_id[binding.telegram_chat_id] = binding
        uninited = get_or_create_presence(binding)
        assert uninited._presence is None
        clear_all_for_tests()

        await upsert_binding(binding)
        assert get_binding(telegram_chat_id) is None

        await restore_persisted_bindings(api=_telegram_api())

        restored = get_binding(telegram_chat_id)
        assert restored is not None
        assert restored.user_id == provision.user_id

        presence = get_or_create_presence(restored)
        assert presence._presence is not None
    finally:
        await stop_all_presences()
        clear_all_for_tests()
        await _cleanup_provision(telegram_chat_id, provision.user_id)
        await async_engine.dispose()
