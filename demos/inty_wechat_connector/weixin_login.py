"""One-shot Weixin QR login (prints QR URL / ASCII for Hermes iLink)."""

from __future__ import annotations

import asyncio
import os

from gateway.platforms.weixin import qr_login
from hermes_constants import get_hermes_home


async def main() -> None:
    home = str(get_hermes_home())
    os.makedirs(home, exist_ok=True)
    cred = await qr_login(home)
    if not cred:
        raise SystemExit("Weixin login failed or timed out")
    print("\nExport these for bridge.py:")
    print(f"export WEIXIN_ACCOUNT_ID={cred['account_id']}")
    print(f"export WEIXIN_TOKEN={cred['token']}")
    if cred.get("base_url"):
        print(f"export WEIXIN_BASE_URL={cred['base_url']}")


if __name__ == "__main__":
    asyncio.run(main())
