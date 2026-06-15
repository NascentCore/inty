"""Tests for telegram_bot_api helpers."""

from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    _GET_UPDATES_URLOPEN_TIMEOUT_SLACK_S,
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


def test_telegram_bot_api_get_me() -> None:
    api = TelegramBotApi(bot_token="token", urlopen=_fake_urlopen)
    me = api.get_me()
    assert me.bot_id == 42
    assert me.username == "demo_bot"


def test_telegram_bot_api_get_text_messages_empty() -> None:
    api = TelegramBotApi(bot_token="token", urlopen=_fake_urlopen)
    messages, next_offset = api.get_text_messages(
        offset=None,
        timeout_seconds=0,
    )
    assert messages == []
    assert next_offset is None


def test_get_text_messages_uses_read_timeout_with_slack() -> None:
    seen_timeouts: list[object] = []

    def capturing_urlopen(request, timeout=15):
        seen_timeouts.append(timeout)
        return _FakeResponse({"ok": True, "result": []})

    api = TelegramBotApi(bot_token="token", urlopen=capturing_urlopen)
    api.get_text_messages(offset=None, timeout_seconds=30)
    assert seen_timeouts == [30 + _GET_UPDATES_URLOPEN_TIMEOUT_SLACK_S]
    assert isinstance(seen_timeouts[0], int)
