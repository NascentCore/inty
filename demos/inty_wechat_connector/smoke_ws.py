"""Smoke-test Inty chat WebSocket without WeChat."""

from __future__ import annotations

import asyncio

from demos.inty_wechat_connector.bridge import ask_inty


async def main() -> None:
    reply = await ask_inty("hello from inty_wechat_connector smoke test")
    print(reply)


if __name__ == "__main__":
    asyncio.run(main())
