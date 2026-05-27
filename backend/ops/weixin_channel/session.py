"""Weixin channel session: transport inbound + Inty WS downlink routing.

Inty WS currently carries text-shaped chat only. Image-only WeChat DMs are answered
with a bridge-side text reply (no ``send_user_text``) so Hermes does not surface
``AssertionError`` from empty user text. Inbound image/video/file/voice CDN handling
is still owned by Hermes ``WeixinAdapter``; see ``transport`` module docstring.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from loguru import logger

from backend.ops.weixin_channel.inty_ws_client import (
    IntyWsChannelClient,
    IntyWsChannelConfig,
)

if TYPE_CHECKING:
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
    """Return a fixed WeChat reply when Inty WS must not be called; else ``None``."""
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
    """One Weixin bot + one long-lived Inty WS for proactive and DM replies.

    TODO(wechat-demo-ws-disconnect-hermes-wording): ``_handle_inbound`` → ``send_user_text``
    ties WeChat DMs to one Inty WS; after Inty :8000 restart the WS is dead until
    ``start()`` / wechat-demo restore, but Hermes still delivers "/reset" error text.
    """

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
        self._ws_client: IntyWsChannelClient | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        from backend.ops.weixin_channel.transport import (
            WeixinCredential,
            WeixinTransport,
        )

        cred = WeixinCredential(
            account_id=self.binding.weixin_account_id,
            token=self.binding.weixin_token,
            base_url=self.binding.weixin_base_url,
        )
        ws_config = IntyWsChannelConfig(
            api_base_url=self.binding.inty_api_base_url,
            jwt=self.binding.inty_jwt,
            agent_id=self.binding.agent_id,
        )
        self._ws_client = IntyWsChannelClient(
            ws_config,
            on_proactive_push=self._handle_proactive_push,
            timezone_name=os.environ.get("TZ"),
        )
        await self._ws_client.connect()
        self._transport = WeixinTransport(
            cred,
            inbound_handler=self._handle_inbound,
        )

    async def run_until_stopped(self) -> None:
        assert self._transport is not None
        try:
            await self._transport.run_until_stopped()
        finally:
            if self._ws_client is not None:
                await self._ws_client.disconnect()

    async def stop(self) -> None:
        self._stop.set()
        if self._transport is not None:
            await self._transport.stop()
        if self._ws_client is not None:
            await self._ws_client.disconnect()

    async def _handle_inbound(self, inbound: WeixinInboundMessage) -> str:
        # TODO(weixin-1to1-binding): last_peer_id is interim; inbound should use bound_peer_id
        # and reject or warn when peer_id != bound peer once 1:1 binding is enforced.
        self.binding.last_peer_id = inbound.peer_id
        self.binding.last_peer_seen_at = datetime.now(timezone.utc)
        peer_updated = self._on_binding_peer_updated
        if peer_updated is not None:
            await peer_updated(self.binding)
        assert self._ws_client is not None
        bridge_reply = weixin_bridge_reply_for_inbound(
            text=inbound.text,
            media_types=inbound.media_types,
        )
        if bridge_reply is not None:
            return bridge_reply
        # TODO(wechat-demo-ws-disconnect-hermes-wording): catch ``ConnectionClosed*`` and
        # return Inty-specific user text (or trigger WS reconnect) instead of Hermes "/reset".
        return await self._ws_client.send_user_text(inbound.text.strip())

    async def _handle_proactive_push(self, text: str) -> None:
        # TODO(weixin-1to1-binding): proactive send targets last_peer_id (latest inbound DM),
        # not the enforced 1:1 bound peer/user; drop or queue until bound_peer_id is set.
        peer_id = self.binding.last_peer_id
        if peer_id is None:
            logger.debug(
                "weixin_channel proactive dropped no_last_peer_id agent_id={}",
                self.binding.agent_id,
            )
            return
        transport = self._transport
        if transport is None:
            return
        try:
            await transport.send_text(peer_id, text)
        except Exception as exc:
            logger.warning(
                "weixin_channel proactive send failed peer_id={} agent_id={}: {}",
                peer_id,
                self.binding.agent_id,
                exc,
            )
