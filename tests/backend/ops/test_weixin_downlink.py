"""WeixinDownlink text forwarding."""

from __future__ import annotations

import pytest

from backend.ops.weixin_channel.weixin_downlink import WeixinDownlink


@pytest.mark.asyncio
async def test_weixin_downlink_send_assistant_text_without_downlink_event() -> (
    None
):
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: "peer-9")
    await downlink.send_assistant_text("inner tick line")
    assert transport.sent == [("peer-9", "inner tick line")]


@pytest.mark.asyncio
async def test_weixin_downlink_send_assistant_text_drops_without_peer_id() -> (
    None
):
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: None)
    await downlink.send_assistant_text("lost")
    assert transport.sent == []


class _RecordingWeixinTransport:
    """Capture ``send_text`` calls for assertions."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, peer_id: str, text: str) -> None:
        self.sent.append((peer_id, text))
