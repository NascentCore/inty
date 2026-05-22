"""Weixin iLink QR login with pollable status (for Ops web demo)."""

from __future__ import annotations

import asyncio
import time
from enum import StrEnum
import aiohttp

from gateway.platforms.weixin import (
    EP_GET_BOT_QR,
    EP_GET_QR_STATUS,
    ILINK_BASE_URL,
    QR_TIMEOUT_MS,
    _api_get,
    _make_ssl_connector,
    save_weixin_account,
)


class WeixinQrPhase(StrEnum):
    FETCHING_QR = "fetching_qr"
    WAIT_SCAN = "wait_scan"
    SCANNED = "scanned"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class WeixinQrFlow:
    """Poll iLink QR status; exposes ``qrcode_url`` for browser display."""

    def __init__(self, hermes_home: str) -> None:
        assert hermes_home != ""
        self._hermes_home = hermes_home
        self.phase = WeixinQrPhase.FETCHING_QR
        self.qrcode_url: str | None = None
        self.qrcode_value: str | None = None
        self.error: str | None = None
        self.credential: dict[str, str] | None = None

    async def run(self, timeout_seconds: int) -> dict[str, str] | None:
        assert timeout_seconds > 0
        bot_type = "3"
        async with aiohttp.ClientSession(
            trust_env=True, connector=_make_ssl_connector()
        ) as session:
            try:
                qr_resp = await _api_get(
                    session,
                    base_url=ILINK_BASE_URL,
                    endpoint=f"{EP_GET_BOT_QR}?bot_type={bot_type}",
                    timeout_ms=QR_TIMEOUT_MS,
                )
            except Exception as exc:
                self.phase = WeixinQrPhase.FAILED
                self.error = f"fetch QR failed: {exc}"
                return None

            qrcode_value = str(qr_resp.get("qrcode") or "")
            qrcode_url = str(qr_resp.get("qrcode_img_content") or "")
            if not qrcode_value:
                self.phase = WeixinQrPhase.FAILED
                self.error = "QR response missing qrcode"
                return None

            self.qrcode_value = qrcode_value
            self.qrcode_url = qrcode_url if qrcode_url else qrcode_value
            self.phase = WeixinQrPhase.WAIT_SCAN

            deadline = time.monotonic() + timeout_seconds
            current_base_url = ILINK_BASE_URL
            refresh_count = 0

            while time.monotonic() < deadline:
                try:
                    status_resp = await _api_get(
                        session,
                        base_url=current_base_url,
                        endpoint=f"{EP_GET_QR_STATUS}?qrcode={qrcode_value}",
                        timeout_ms=QR_TIMEOUT_MS,
                    )
                except asyncio.TimeoutError:
                    await asyncio.sleep(1)
                    continue
                except Exception as exc:
                    await asyncio.sleep(1)
                    continue

                status = str(status_resp.get("status") or "wait")
                match status:
                    case "wait":
                        self.phase = WeixinQrPhase.WAIT_SCAN
                    case "scaned":
                        self.phase = WeixinQrPhase.SCANNED
                    case "scaned_but_redirect":
                        redirect_host = str(status_resp.get("redirect_host") or "")
                        if redirect_host:
                            current_base_url = f"https://{redirect_host}"
                    case "expired":
                        refresh_count += 1
                        if refresh_count > 3:
                            self.phase = WeixinQrPhase.FAILED
                            self.error = "QR expired too many times"
                            return None
                        try:
                            qr_resp = await _api_get(
                                session,
                                base_url=ILINK_BASE_URL,
                                endpoint=f"{EP_GET_BOT_QR}?bot_type={bot_type}",
                                timeout_ms=QR_TIMEOUT_MS,
                            )
                            qrcode_value = str(qr_resp.get("qrcode") or "")
                            qrcode_url = str(qr_resp.get("qrcode_img_content") or "")
                            self.qrcode_value = qrcode_value
                            self.qrcode_url = (
                                qrcode_url if qrcode_url else qrcode_value
                            )
                            self.phase = WeixinQrPhase.WAIT_SCAN
                        except Exception as exc:
                            self.phase = WeixinQrPhase.FAILED
                            self.error = f"QR refresh failed: {exc}"
                            return None
                    case "confirmed":
                        account_id = str(status_resp.get("ilink_bot_id") or "")
                        token = str(status_resp.get("bot_token") or "")
                        base_url = str(status_resp.get("baseurl") or ILINK_BASE_URL)
                        user_id = str(status_resp.get("ilink_user_id") or "")
                        if not account_id or not token:
                            self.phase = WeixinQrPhase.FAILED
                            self.error = "confirmed but credential incomplete"
                            return None
                        save_weixin_account(
                            self._hermes_home,
                            account_id=account_id,
                            token=token,
                            base_url=base_url,
                            user_id=user_id,
                        )
                        cred = {
                            "account_id": account_id,
                            "token": token,
                            "base_url": base_url,
                            "user_id": user_id,
                        }
                        self.credential = cred
                        self.phase = WeixinQrPhase.CONFIRMED
                        return cred
                    case _:
                        pass
                await asyncio.sleep(1)

        self.phase = WeixinQrPhase.TIMEOUT
        self.error = "Weixin login timed out"
        return None
