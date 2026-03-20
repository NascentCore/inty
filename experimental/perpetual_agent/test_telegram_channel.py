from __future__ import annotations

import json
import urllib.parse

from experimental.perpetual_agent.living_companion import ChannelType
from experimental.perpetual_agent.telegram_channel import (
    TelegramBotApi,
    TelegramChannelTransport,
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
                            },
                        },
                        {
                            "update_id": 12,
                            "message": {
                                "chat": {"id": 12345},
                            },
                        },
                        {"update_id": 13, "edited_message": {"chat": {"id": 12345}}},
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
    assert len(messages) == 1
    assert messages[0].chat_id == "12345"
    assert messages[0].text == "hello"


def test_send_message_posts_expected_payload() -> None:
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self):
            return json.dumps({"ok": True, "result": {"message_id": 99}}).encode("utf-8")

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


def test_telegram_transport_sends_and_returns_outbound_event() -> None:
    sent: list[tuple[str, str]] = []

    class _FakeTelegramBotApi:
        def send_message(self, *, chat_id: str, text: str):
            sent.append((chat_id, text))
            return {"ok": True}

    transport = TelegramChannelTransport(bot_api=_FakeTelegramBotApi())  # type: ignore[arg-type]
    event = transport.send(
        channel=ChannelType.TELEGRAM,
        recipient="8888",
        content="reply content",
        metadata={"m": "v"},
    )

    assert sent == [("8888", "reply content")]
    assert event.channel == ChannelType.TELEGRAM
    assert event.recipient == "8888"
