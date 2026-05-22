"""Run Hermes WeixinAdapter long-poll bridge into Inty chat WebSocket."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from gateway.config import PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.platforms.weixin import WeixinAdapter

from demos.inty_wechat_connector.inty_ws_client import IntyWsConnection, ask_inty


@dataclass(frozen=True)
class WeixinCredential:
    account_id: str
    token: str
    base_url: str


class WeixinBridgeRunner:
    """One WeixinAdapter + Inty WS handler; ``stop`` disconnects the adapter."""

    def __init__(self, cred: WeixinCredential, inty: IntyWsConnection) -> None:
        self._cred = cred
        self._inty = inty
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
            return await ask_inty(event.text, self._inty)

        adapter.set_message_handler(handle_weixin_message)
        self._adapter = adapter
        await adapter.connect()
        while not self._stop.is_set():
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._stop.set()
        if self._adapter is not None:
            await self._adapter.disconnect()
            self._adapter = None
