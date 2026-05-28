"""Unit tests for ``WeixinQrFlow`` onboard vs legacy QR behavior."""

from __future__ import annotations

import asyncio

import pytest

from backend.ops.weixin_channel import weixin_qr_flow as qr_mod
from backend.ops.weixin_channel.ilink_qr_client import EP_GET_BOT_QR, EP_GET_QR_STATUS
from backend.ops.weixin_channel.weixin_qr_flow import (
    QRCODE_EXPIRED_ERROR,
    WeixinQrFlow,
    WeixinQrPhase,
)


@pytest.mark.asyncio
async def test_onboard_expired_fails_without_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
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
            return {"qrcode": "qv1", "qrcode_img_content": "https://qr.example/1"}
        if EP_GET_QR_STATUS in endpoint:
            return {"status": "expired"}
        return {"status": "wait"}

    monkeypatch.setattr(qr_mod, "ilink_api_get", fake_ilink_api_get)

    flow = WeixinQrFlow(
        persist_hermes_account=False,
        hermes_home="",
        refresh_on_expired=False,
    )
    cred = await flow.run(timeout_seconds=30)
    assert cred is None
    assert flow.phase == WeixinQrPhase.FAILED
    assert flow.error == QRCODE_EXPIRED_ERROR
    assert call == 2


@pytest.mark.asyncio
async def test_legacy_expired_refreshes_qr(monkeypatch: pytest.MonkeyPatch) -> None:
    bot_qr_calls = 0

    async def fake_ilink_api_get(
        _session: object,
        *,
        base_url: str,
        endpoint: str,
        timeout_ms: int,
    ) -> dict[str, object]:
        del base_url, timeout_ms
        nonlocal bot_qr_calls
        if EP_GET_BOT_QR in endpoint:
            bot_qr_calls += 1
            return {
                "qrcode": f"qv{bot_qr_calls}",
                "qrcode_img_content": f"https://qr.example/{bot_qr_calls}",
            }
        if EP_GET_QR_STATUS in endpoint:
            if bot_qr_calls == 1:
                return {"status": "expired"}
            return {"status": "wait"}
        return {"status": "wait"}

    monkeypatch.setattr(qr_mod, "ilink_api_get", fake_ilink_api_get)

    flow = WeixinQrFlow(
        persist_hermes_account=True,
        hermes_home="/tmp/hermes-test-home",
        refresh_on_expired=True,
    )
    qr_task = asyncio.create_task(flow.run(timeout_seconds=5))
    for _ in range(100):
        if bot_qr_calls >= 2:
            break
        await asyncio.sleep(0.05)
    qr_task.cancel()
    try:
        await qr_task
    except asyncio.CancelledError:
        pass
    assert bot_qr_calls >= 2


@pytest.mark.asyncio
async def test_onboard_confirmed_skips_save_weixin_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved: list[str] = []

    def fake_save(
        hermes_home: str,
        *,
        account_id: str,
        token: str,
        base_url: str,
        user_id: str,
    ) -> None:
        del token, base_url, user_id
        saved.append(hermes_home + ":" + account_id)

    async def fake_ilink_api_get(
        _session: object,
        *,
        base_url: str,
        endpoint: str,
        timeout_ms: int,
    ) -> dict[str, object]:
        del base_url, timeout_ms
        if EP_GET_BOT_QR in endpoint:
            return {"qrcode": "qv3", "qrcode_img_content": "https://qr.example/3"}
        if EP_GET_QR_STATUS in endpoint:
            return {
                "status": "confirmed",
                "ilink_bot_id": "bot-1",
                "bot_token": "tok-1",
                "ilink_user_id": "user-1",
            }
        return {"status": "wait"}

    monkeypatch.setattr(qr_mod, "ilink_api_get", fake_ilink_api_get)
    monkeypatch.setattr(qr_mod, "save_weixin_account", fake_save)

    flow = WeixinQrFlow(
        persist_hermes_account=False,
        hermes_home="",
        refresh_on_expired=False,
    )
    cred = await flow.run(timeout_seconds=30)
    assert cred is not None
    assert cred["account_id"] == "bot-1"
    assert saved == []
