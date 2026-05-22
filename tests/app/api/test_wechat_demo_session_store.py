"""Regression tests for Ops WeChat demo session state handling."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.ops.schemas.wechat_demo import WechatDemoSessionCreate
from backend.ops.wechat_demo import session_store


def test_session_create_rejects_whitespace_only_credentials() -> None:
    with pytest.raises(ValidationError):
        WechatDemoSessionCreate(
            inty_api_base_url="   ",
            inty_jwt="   ",
            agent_id="   ",
        )


@pytest.mark.asyncio
async def test_stopped_session_ignores_late_lifecycle_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeQrFlow:
        phase = type("FakePhase", (), {"value": "qr_login"})()
        qrcode_url = None
        error = None

        def __init__(self, hermes_home: str) -> None:
            assert hermes_home

        async def run(self, timeout_seconds: int) -> None:
            assert timeout_seconds > 0
            raise RuntimeError("late failure after stop")

    monkeypatch.setattr(
        session_store,
        "_import_wechat_demo_runtime",
        lambda: (
            object,
            object,
            object,
            FakeQrFlow,
            lambda: "/tmp/inty-wechat-demo-test",
        ),
    )
    session = session_store._WechatDemoSession(
        session_id="session-test",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        phase=session_store._StorePhase.STOPPED,
    )

    await session_store._run_session_lifecycle(session)

    assert session.phase == session_store._StorePhase.STOPPED
    assert session.error is None
