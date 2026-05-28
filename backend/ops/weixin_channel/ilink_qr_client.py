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
- **User re-login after ``-14``**: cannot push re-scan QR through WeChat DM (token dead);
  see ``TODO(wechat-demo-ilink-session-expired-user-notify)`` in ``transport`` module doc.
- **WeChat user presence**: the iLink Bot API exposed here (``getupdates``,
  ``sendmessage``, QR login, etc.) does **not** report whether a chatter opened WeChat,
  opened the bot DM thread, or is online. Inbound activity is DM payloads only; there is
  no read receipt, enter-session, or peer-typing event on this wire. Do not infer
  presence from ``last_peer_seen_at`` (that is last inbound message time).
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
ILINK_RATE_LIMIT_ERRCODE = -2

# Shown on wechat-demo session poll when bridge tears down after iLink session end.
ILINK_SESSION_EXPIRED_USER_MESSAGE = (
    "iLink session expired (errcode=-14). Re-scan QR at Ops /wechat-demo."
)


def is_ilink_session_expired(
    ret: int | None,
    errcode: int | None,
    errmsg: str | None,
) -> bool:
    """True when iLink signals bot_token is dead (Hermes ``WeixinAdapter`` parity)."""
    if (
        ret == ILINK_SESSION_EXPIRED_ERRCODE
        or errcode == ILINK_SESSION_EXPIRED_ERRCODE
    ):
        return True
    if ret != ILINK_RATE_LIMIT_ERRCODE and errcode != ILINK_RATE_LIMIT_ERRCODE:
        return False
    return (errmsg or "").lower() == "unknown error"


def is_ilink_session_expired_runtime_error(exc: BaseException) -> bool:
    """Parse Hermes ``RuntimeError`` from ``sendmessage`` for session-expired codes."""
    if not isinstance(exc, RuntimeError):
        return False
    text = str(exc)
    errcode: int | None = None
    ret: int | None = None
    errmsg: str | None = None
    for part in text.replace(",", " ").split():
        if part.startswith("errcode="):
            try:
                errcode = int(part.split("=", 1)[1])
            except ValueError:
                pass
        elif part.startswith("ret="):
            try:
                ret = int(part.split("=", 1)[1])
            except ValueError:
                pass
        elif part.startswith("errmsg="):
            errmsg = part.split("=", 1)[1]
    return is_ilink_session_expired(ret, errcode, errmsg)


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
