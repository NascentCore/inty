"""Hermes ``WeixinAdapter`` transport for Ops Weixin channel."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from gateway.config import PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.platforms.weixin import WeixinAdapter
from loguru import logger


@dataclass(frozen=True)
class WeixinCredential:
    """iLink bot credential after QR login."""

    account_id: str
    token: str
    base_url: str


@dataclass(frozen=True)
class WeixinInboundMessage:
    """Normalized inbound DM from Weixin iLink."""

    account_id: str
    peer_id: str
    text: str


WeixinInboundHandler = Callable[[WeixinInboundMessage], Awaitable[str]]


class WeixinTransport:
    """Long-poll Weixin DM transport; delegates replies to ``inbound_handler``."""

    def __init__(
        self,
        cred: WeixinCredential,
        inbound_handler: WeixinInboundHandler,
    ) -> None:
        assert cred.account_id != ""
        assert cred.token != ""
        assert cred.base_url != ""
        self._cred = cred
        self._inbound_handler = inbound_handler
        self._adapter: WeixinAdapter | None = None
        self._stop = asyncio.Event()

    async def run_until_stopped(self) -> None:
        config = PlatformConfig(
            enabled=True,
            token=self._cred.token,
            extra={
                "account_id": self._cred.account_id,
                "base_url": self._cred.base_url,
                "dm_policy": "open",
                "group_policy": "disabled",
            },
        )
        adapter = WeixinAdapter(config)

        async def handle_weixin_message(event: MessageEvent) -> str:
            peer_id = event.source.chat_id
            assert peer_id != ""
            inbound = WeixinInboundMessage(
                account_id=self._cred.account_id,
                peer_id=peer_id,
                text=event.text,
            )
            return await self._inbound_handler(inbound)

        adapter.set_message_handler(handle_weixin_message)
        self._adapter = adapter
        await adapter.connect()
        while not self._stop.is_set():
            await asyncio.sleep(1)

    async def send_text(self, peer_id: str, text: str) -> None:
        assert peer_id != ""
        assert text != ""
        adapter = self._adapter
        assert adapter is not None
        result = await adapter.send(peer_id, text)
        if not getattr(result, "success", True):
            logger.warning(
                "weixin_transport send_text failed peer_id={} result={}",
                peer_id,
                result,
            )
            raise RuntimeError(f"Weixin send failed: {result}")

    async def stop(self) -> None:
        self._stop.set()
        if self._adapter is not None:
            await self._adapter.disconnect()
            self._adapter = None
