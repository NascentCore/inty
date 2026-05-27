"""Weixin channel session: transport inbound + in-process companion presence.

Inty WS currently carries text-shaped chat only. Image-only WeChat DMs are answered
with a bridge-side text reply (no companion turn) so Hermes does not surface
``AssertionError`` from empty user text. Inbound image/video/file/voice CDN handling
is still owned by Hermes ``WeixinAdapter``; see ``transport`` module docstring.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from backend.ops.weixin_channel.inprocess_presence import WeixinInprocessPresence
    from backend.ops.weixin_channel.transport import (
        WeixinCredential,
        WeixinInboundMessage,
        WeixinTransport,
    )


def weixin_bridge_reply_for_inbound(
    *,
    text: str,
    media_types: tuple[str, ...],
) -> str | None:
    """Return a fixed WeChat reply when companion must not be called; else ``None``."""
    stripped = text.strip()
    has_image = any(media_type.startswith("image/") for media_type in media_types)
    if has_image and not stripped:
        return (
            "This WeChat demo bridge can only forward text right now. "
            "Please send your message as text (images are not passed through to the companion yet)."
        )
    if not stripped:
        return (
            "Please send a text message. "
            "This bridge cannot forward images or other attachments without text yet."
        )
    return None


@dataclass
class WeixinChannelBinding:
    """Binding for one Ops demo session (bridge fields persisted in Postgres).

    ``weixin_token`` is iLink ``bot_token`` after QR confirm. No API TTL field — session
    ends at ``errcode=-14`` (``ILINK_SESSION_EXPIRED_ERRCODE``); then re-scan QR.

    TODO(weixin-1to1-binding): Ops wechat-demo rule — one agent ↔ one Inty user_id ↔
    one WeChat peer_id; reject a second peer or user on the same agent. Persist and
    enforce at bind time (not via last_peer_id heuristics). Registry/API likely in
    wechat_demo session_store plus Ops wechat-demo routes.
    """

    # Demo session UUID today; not the enforced 1:1 Inty user until binding is implemented.
    user_id: str
    agent_id: str
    inty_api_base_url: str
    inty_jwt: str
    weixin_account_id: str
    weixin_token: str
    weixin_base_url: str
    # Interim: most recent inbound WeChat DM peer; replace with explicit bound_peer_id.
    last_peer_id: str | None = None
    last_peer_seen_at: datetime | None = None


class WeixinChannelSession:
    """One Weixin bot + in-process companion presence (no ``/api/v1/chat/ws`` loopback)."""

    def __init__(
        self,
        binding: WeixinChannelBinding,
        on_binding_peer_updated: (
            Callable[[WeixinChannelBinding], Awaitable[None]] | None
        ),
    ) -> None:
        self.binding = binding
        self._on_binding_peer_updated = on_binding_peer_updated
        self._transport: WeixinTransport | None = None
        self._presence: WeixinInprocessPresence | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        from backend.ops.weixin_channel.inprocess_presence import (
            WeixinInprocessPresence,
        )
        from backend.ops.weixin_channel.transport import (
            WeixinCredential,
            WeixinTransport,
        )

        cred = WeixinCredential(
            account_id=self.binding.weixin_account_id,
            token=self.binding.weixin_token,
            base_url=self.binding.weixin_base_url,
        )
        self._presence = WeixinInprocessPresence(self.binding)
        self._transport = WeixinTransport(
            cred,
            inbound_handler=self._handle_inbound,
        )
        await self._presence.start(self._transport)

    async def run_until_stopped(self) -> None:
        assert self._transport is not None
        await self._transport.run_until_stopped()

    async def stop(self) -> None:
        self._stop.set()
        if self._transport is not None:
            await self._transport.stop()
        if self._presence is not None:
            await self._presence.stop()

    async def _handle_inbound(self, inbound: WeixinInboundMessage) -> str:
        # TODO(weixin-1to1-binding): last_peer_id is interim; inbound should use bound_peer_id
        # and reject or warn when peer_id != bound peer once 1:1 binding is enforced.
        self.binding.last_peer_id = inbound.peer_id
        self.binding.last_peer_seen_at = datetime.now(timezone.utc)
        peer_updated = self._on_binding_peer_updated
        if peer_updated is not None:
            await peer_updated(self.binding)
        bridge_reply = weixin_bridge_reply_for_inbound(
            text=inbound.text,
            media_types=inbound.media_types,
        )
        if bridge_reply is not None:
            return bridge_reply
        assert self._presence is not None
        return await self._presence.handle_user_text(inbound.text.strip())
