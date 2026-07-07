"""Weixin text sink: plain assistant text to Hermes ``send_text``.

TODO(weixin-reply-reaction-downlink): Quote/reply threading + emoji reactions on outbound
  when Hermes/iLink supports them — #3442 (epic #3440)
TODO(!3452): Dispatch image-bearing outbound events to Hermes native WeChat image bubbles.

Each ``send_assistant_text`` call passes one plain-text string to
``WeixinTransport.send_text``. Hermes later decides whether that string appears
as one or several WeChat bubbles. See ``transport`` and
``config.yaml`` ``weixin_channel.split_multiline_messages``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class WeixinTextTransport(Protocol):
    """Minimal outbound text surface (``WeixinTransport.send_text``)."""

    async def send_text(self, peer_id: str, text: str) -> None:
        """Send plain text to one WeChat peer."""


WeixinPeerIdResolver = Callable[[], str | None]


class WeixinDownlink:
    """Deliver companion assistant text as Weixin DM plain text."""

    def __init__(
        self,
        transport: WeixinTextTransport,
        peer_id_resolver: WeixinPeerIdResolver,
    ) -> None:
        assert transport is not None
        assert peer_id_resolver is not None
        self._transport = transport
        self._peer_id_resolver = peer_id_resolver

    async def send_assistant_text(self, text: str) -> None:
        """Push plain assistant text to the current WeChat peer (inner-tick / proactive)."""
        stripped = text.strip()
        if not stripped:
            return
        peer_id = self._peer_id_resolver()
        if peer_id is None:
            return
        await self._transport.send_text(peer_id, stripped)
