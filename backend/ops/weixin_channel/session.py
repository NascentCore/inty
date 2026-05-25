"""Weixin channel session: transport inbound + Inty WS downlink routing."""

from __future__ import annotations

import asyncio
import os
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


@dataclass
class WeixinChannelBinding:
    """In-memory binding for one Ops demo session (lost on restart)."""

    user_id: str
    agent_id: str
    inty_api_base_url: str
    inty_jwt: str
    weixin_account_id: str
    weixin_token: str
    weixin_base_url: str
    last_peer_id: str | None = None
    last_peer_seen_at: datetime | None = None


class WeixinChannelSession:
    """One Weixin bot + one long-lived Inty WS for proactive and DM replies."""

    def __init__(self, binding: WeixinChannelBinding) -> None:
        self.binding = binding
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
        self.binding.last_peer_id = inbound.peer_id
        self.binding.last_peer_seen_at = datetime.now(timezone.utc)
        assert self._ws_client is not None
        return await self._ws_client.send_user_text(inbound.text)

    async def _handle_proactive_push(self, text: str) -> None:
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
