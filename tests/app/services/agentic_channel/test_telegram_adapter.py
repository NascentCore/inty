"""Tests for Telegram channel adapter downlink."""

from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from app.services.agentic_channel.adapters.telegram import TelegramChannelAdapter
from app.services.agentic_companion.downlink import Downlink, DownlinkKind


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
    if url.endswith("/sendMessage"):
        return _FakeResponse({"ok": True, "result": {}})
    raise HTTPError(url, 404, "not found", hdrs=None, fp=BytesIO())


@pytest.mark.asyncio
async def test_telegram_adapter_deliver_proactive() -> None:
    from app.external_services.telegram_bot_api import TelegramBotApi

    sent: list[str] = []

    def _capture_urlopen(request, timeout=15):
        sent.append(request.data.decode("utf-8"))
        return _fake_urlopen(request, timeout)

    api = TelegramBotApi(bot_token="test-token", urlopen=_capture_urlopen)
    adapter = TelegramChannelAdapter(api=api, channel_address="5078060274")
    downlink = adapter.as_downlink()
    await downlink.deliver(
        Downlink(
            kind=DownlinkKind.PROACTIVE,
            assistant_text="hello",
            turn=None,
            tool_output=None,
            bootstrap_interim=None,
            scheduled_task_id=None,
            transcript_user_text=None,
        )
    )
    assert "5078060274" in sent[0]
    assert "hello" in sent[0]


@pytest.mark.asyncio
async def test_telegram_adapter_strips_leading_transcript_timestamp_prefixes() -> None:
    from app.external_services.telegram_bot_api import TelegramBotApi

    sent: list[str] = []

    def _capture_urlopen(request, timeout=15):
        sent.append(request.data.decode("utf-8"))
        return _fake_urlopen(request, timeout)

    api = TelegramBotApi(bot_token="test-token", urlopen=_capture_urlopen)
    adapter = TelegramChannelAdapter(api=api, channel_address="5078060274")
    downlink = adapter.as_downlink()
    await downlink.deliver(
        Downlink(
            kind=DownlinkKind.USER_REPLY,
            assistant_text=(
                "[2026-05-30 13:09:06 UTC] [2026-05-30 13:10:00 UTC] hello"
            ),
            turn=None,
            tool_output=None,
            bootstrap_interim=None,
            scheduled_task_id=None,
            transcript_user_text=None,
        )
    )
    assert "hello" in sent[0]
    assert "%5B2026-05-30" not in sent[0]
