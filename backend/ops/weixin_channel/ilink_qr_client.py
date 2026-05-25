"""iLink Bot API HTTP helpers for Weixin QR login (Ops ``weixin_channel``).

Owns the QR login wire protocol so ``weixin_qr_flow`` does not depend on Hermes
private symbols (``gateway.platforms.weixin._api_get``, etc.).

TODO(weixin-upstream-parity): Periodically align with the Hermes Agent project
(Weixin messaging user guide, release notes, ``gateway.platforms.weixin``) and
with community iLink client implementations. Tencent's iLink Bot API
(``ILINK_BASE_URL``, endpoints, QR login headers such as ``iLink-App-ClientVersion``,
media/CDN flows) is not published like MP/WeCom Open Platform contracts—it can
drift; our QR wire helpers can desync from ``WeixinAdapter`` unless we track upstream.
iLink time limits (not documented as a fixed wall-clock TTL on the wire):

- **QR poll token** (``qrcode`` query param): short-lived; ``get_qrcode_status`` may
  return ``status=expired`` (refresh ``get_bot_qrcode``). No ``14``-minute field.
- **QR login client budget**: callers pass ``timeout_seconds`` (wechat-demo uses
  ``WECHAT_DEMO_QR_LOGIN_POLL_TIMEOUT_SECONDS`` = 480s / 8 min).
- **Post-login ``bot_token``** (bridge ``weixin_token``), after QR ``status=confirmed``:
  iLink does **not** return ``expires_in``, ``valid_until``, or any TTL. There is no
  documented wall-clock lifetime (not 14 minutes — do not confuse with ``errcode=-14``).
  The token stays usable until ``getupdates`` / ``sendmessage`` fail with
  ``errcode=-14`` (session expired); then re-scan QR. Hermes: ``SESSION_EXPIRED_ERRCODE``.
  Empirical lifetime varies (hours to days reported); Ops must not assume a fixed duration.
"""

from __future__ import annotations

import json
import ssl
from typing import Any

import aiohttp
import certifi

ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
ILINK_APP_ID = "bot"
ILINK_APP_CLIENT_VERSION = (2 << 16) | (2 << 8) | 0
EP_GET_BOT_QR = "ilink/bot/get_bot_qrcode"
EP_GET_QR_STATUS = "ilink/bot/get_qrcode_status"
QR_TIMEOUT_MS = 35_000

# Post-QR bot_token session end signal (iLink wire + Hermes gateway.platforms.weixin).
ILINK_SESSION_EXPIRED_ERRCODE = -14


def make_ilink_ssl_connector() -> aiohttp.TCPConnector:
    """TCPConnector using certifi CA bundle for Tencent iLink TLS verification."""
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    return aiohttp.TCPConnector(ssl=ssl_ctx)


async def ilink_api_get(
    session: aiohttp.ClientSession,
    *,
    base_url: str,
    endpoint: str,
    timeout_ms: int,
) -> dict[str, Any]:
    """GET one iLink Bot API endpoint and parse JSON body."""
    assert base_url != ""
    assert endpoint != ""
    assert timeout_ms > 0
    url = f"{base_url.rstrip('/')}/{endpoint}"
    headers = {
        "iLink-App-Id": ILINK_APP_ID,
        "iLink-App-ClientVersion": str(ILINK_APP_CLIENT_VERSION),
    }
    timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000)
    async with session.get(url, headers=headers, timeout=timeout) as response:
        raw = await response.text()
        if not response.ok:
            raise RuntimeError(
                f"iLink GET {endpoint} HTTP {response.status}: {raw[:200]}"
            )
        return json.loads(raw)
