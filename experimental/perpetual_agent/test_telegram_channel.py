from __future__ import annotations

import json
import time
import urllib.parse

from experimental.perpetual_agent.living_companion import ChannelType
from experimental.perpetual_agent.telegram_channel import (
    TelegramBotApi,
    format_epoch_for_local_log,
)


def test_get_text_messages_filters_non_text_and_returns_next_offset() -> None:
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self):
            return json.dumps(
                {
                    "ok": True,
                    "result": [
                        {
                            "update_id": 11,
                            "message": {
                                "chat": {"id": 12345},
                                "text": "hello",
                                "date": 1700000000,
                            },
                        },
                        {
                            "update_id": 12,
                            "message": {
                                "chat": {"id": 12345},
                            },
                        },
                        {
                            "update_id": 13,
                            "edited_message": {"chat": {"id": 12345}},
                        },
                    ],
                }
            ).encode("utf-8")

    captured: dict[str, object] = {}

    def _fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["timeout"] = timeout
        return _FakeResponse()

    api = TelegramBotApi(bot_token="token123", urlopen=_fake_urlopen)
    messages, next_offset = api.get_text_messages(offset=10, timeout_seconds=20)

    query = urllib.parse.parse_qs(urllib.parse.urlsplit(captured["url"]).query)
    assert query["timeout"] == ["20"]
    assert query["offset"] == ["10"]
    assert captured["method"] == "GET"
    assert captured["timeout"] == 25
    assert next_offset == 14


def test_get_text_messages_one_local_received_at_per_payload(
    monkeypatch,
) -> None:  # noqa: ANN001
    """All text messages from one getUpdates JSON share the same receive timestamp."""

    time_calls: list[float] = []

    def _fake_time() -> float:
        time_calls.append(1000.0 + 0.01 * len(time_calls))
        return time_calls[-1]

    monkeypatch.setattr(
        "experimental.perpetual_agent.telegram_channel.time.time", _fake_time
    )

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self):
            return json.dumps(
                {
                    "ok": True,
                    "result": [
                        {
                            "update_id": 1,
                            "message": {
                                "chat": {"id": 1},
                                "text": "a",
                                "date": 1700000000,
                            },
                        },
                        {
                            "update_id": 2,
                            "message": {
                                "chat": {"id": 1},
                                "text": "b",
                                "date": 1700000001,
                            },
                        },
                    ],
                }
            ).encode("utf-8")

    def _fake_urlopen(request, timeout):  # noqa: ANN001
        return _FakeResponse()

    api = TelegramBotApi(bot_token="t", urlopen=_fake_urlopen)
    messages, _next = api.get_text_messages(offset=None, timeout_seconds=1)

    assert len(messages) == 2
    assert (
        messages[0].local_received_at == messages[1].local_received_at == 1000.0
    )
    assert len(time_calls) == 1


def test_get_text_messages_allows_zero_timeout_for_short_polling() -> None:
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self):
            return json.dumps({"ok": True, "result": []}).encode("utf-8")

    captured: dict[str, object] = {}

    def _fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return _FakeResponse()

    api = TelegramBotApi(bot_token="token123", urlopen=_fake_urlopen)
    messages, _next = api.get_text_messages(offset=None, timeout_seconds=0)

    query = urllib.parse.parse_qs(urllib.parse.urlsplit(captured["url"]).query)
    assert query["timeout"] == ["0"]
    assert captured["timeout"] == 5
    assert messages == []


def test_send_message_posts_expected_payload() -> None:
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self):
            return json.dumps(
                {"ok": True, "result": {"message_id": 99}}
            ).encode("utf-8")

    captured: dict[str, object] = {}

    def _fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["body"] = request.data.decode("utf-8")
        captured["timeout"] = timeout
        return _FakeResponse()

    api = TelegramBotApi(bot_token="token123", urlopen=_fake_urlopen)
    payload = api.send_message(chat_id="4567", text="hello telegram")

    encoded = urllib.parse.parse_qs(captured["body"])
    assert captured["url"].endswith("/bottoken123/sendMessage")
    assert captured["method"] == "POST"
    assert captured["timeout"] == 15
    assert encoded["chat_id"] == ["4567"]
    assert encoded["text"] == ["hello telegram"]
    assert payload["ok"] is True


def test_format_epoch_for_local_log_missing() -> None:
    assert format_epoch_for_local_log(None) == "n/a"


def test_format_epoch_for_local_log_utc_tz(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("TZ", "UTC")
    if hasattr(time, "tzset"):
        time.tzset()
    assert format_epoch_for_local_log(0) == "1970-01-01 00:00:00 +0000"
