"""Tests for telegram_bot_api helpers."""

from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import parse_qs


from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    TelegramParseMode,
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


def test_telegram_bot_api_send_message_includes_parse_mode_when_set() -> None:
    captured: list[bytes] = []

    def capturing_urlopen(request, timeout=15):
        if request.full_url.endswith("/sendMessage"):
            captured.append(request.data)
            return _FakeResponse({"ok": True, "result": {}})
        raise HTTPError(
            request.full_url, 404, "not found", hdrs=None, fp=BytesIO()
        )

    api = TelegramBotApi(bot_token="token", urlopen=capturing_urlopen)
    api.send_message(
        chat_id="123",
        text="<i>hello</i>",
        parse_mode=TelegramParseMode.HTML,
    )
    assert len(captured) == 1
    fields = parse_qs(captured[0].decode("utf-8"))
    assert fields["parse_mode"] == ["HTML"]
    assert fields["text"] == ["<i>hello</i>"]


def test_telegram_bot_api_send_message_omits_parse_mode_when_none() -> None:
    captured: list[bytes] = []

    def capturing_urlopen(request, timeout=15):
        if request.full_url.endswith("/sendMessage"):
            captured.append(request.data)
            return _FakeResponse({"ok": True, "result": {}})
        raise HTTPError(
            request.full_url, 404, "not found", hdrs=None, fp=BytesIO()
        )

    api = TelegramBotApi(bot_token="token", urlopen=capturing_urlopen)
    api.send_message(chat_id="123", text="plain", parse_mode=None)
    assert len(captured) == 1
    fields = parse_qs(captured[0].decode("utf-8"))
    assert "parse_mode" not in fields
    assert fields["text"] == ["plain"]
