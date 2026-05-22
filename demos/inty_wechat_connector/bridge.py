"""Minimal WeChat (Hermes WeixinAdapter) -> Inty companion WebSocket bridge."""

from __future__ import annotations

import asyncio
import os

from demos.inty_wechat_connector.inty_ws_client import IntyWsConnection
from demos.inty_wechat_connector.weixin_bridge import (
    WeixinBridgeRunner,
    WeixinCredential,
)


async def ask_inty(user_text: str) -> str:
    """CLI/env wrapper around :func:`inty_ws_client.ask_inty`."""
    from demos.inty_wechat_connector.inty_ws_client import ask_inty as _ask_inty

    conn = IntyWsConnection(
        api_base_url=os.environ["INTY_API_BASE_URL"],
        jwt=os.environ["INTY_JWT"],
        agent_id=os.environ["INTY_AGENT_ID"],
    )
    return await _ask_inty(user_text, conn)


async def main() -> None:
    cred = WeixinCredential(
        account_id=os.environ["WEIXIN_ACCOUNT_ID"],
        token=os.environ["WEIXIN_TOKEN"],
        base_url=os.getenv("WEIXIN_BASE_URL", "https://ilinkai.weixin.qq.com"),
    )
    inty = IntyWsConnection(
        api_base_url=os.environ["INTY_API_BASE_URL"],
        jwt=os.environ["INTY_JWT"],
        agent_id=os.environ["INTY_AGENT_ID"],
    )
    runner = WeixinBridgeRunner(cred, inty)
    await runner.run_until_stopped()


if __name__ == "__main__":
    asyncio.run(main())
