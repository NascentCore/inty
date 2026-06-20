"""Unit tests for ``WeixinQrFlow`` onboard QR behavior."""

from __future__ import annotations

import pytest

from backend.ops.weixin_channel import weixin_qr_flow as qr_mod
from backend.ops.weixin_channel.ilink_qr_client import (
    EP_GET_BOT_QR,
    EP_GET_QR_STATUS,
)
from backend.ops.weixin_channel.weixin_qr_flow import (
    QRCODE_EXPIRED_ERROR,
    WeixinQrFlow,
    WeixinQrPhase,
)


@pytest.mark.asyncio
async def test_onboard_expired_fails_without_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call = 0

    async def fake_ilink_api_get(
        _session: object,
        *,
        base_url: str,
        endpoint: str,
        timeout_ms: int,
    ) -> dict[str, object]:
        del base_url, timeout_ms
        nonlocal call
        call += 1
        if EP_GET_BOT_QR in endpoint:
            return {
                "qrcode": "qv1",
                "qrcode_img_content": "https://qr.example/1",
            }
        if EP_GET_QR_STATUS in endpoint:
            return {"status": "expired"}
        return {"status": "wait"}

    monkeypatch.setattr(qr_mod, "ilink_api_get", fake_ilink_api_get)

    flow = WeixinQrFlow()
    cred = await flow.run(timeout_seconds=30)
    assert cred is None
    assert flow.phase == WeixinQrPhase.FAILED
    assert flow.error == QRCODE_EXPIRED_ERROR
    assert call == 2


@pytest.mark.asyncio
async def test_onboard_confirmed_returns_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_ilink_api_get(
        _session: object,
        *,
        base_url: str,
        endpoint: str,
        timeout_ms: int,
    ) -> dict[str, object]:
        del base_url, timeout_ms
        if EP_GET_BOT_QR in endpoint:
            return {
                "qrcode": "qv3",
                "qrcode_img_content": "https://qr.example/3",
            }
        if EP_GET_QR_STATUS in endpoint:
            return {
                "status": "confirmed",
                "ilink_bot_id": "bot-1",
                "bot_token": "tok-1",
                "ilink_user_id": "user-1",
            }
        return {"status": "wait"}

    monkeypatch.setattr(qr_mod, "ilink_api_get", fake_ilink_api_get)

    flow = WeixinQrFlow()
    cred = await flow.run(timeout_seconds=30)
    assert cred is not None
    assert cred["account_id"] == "bot-1"
