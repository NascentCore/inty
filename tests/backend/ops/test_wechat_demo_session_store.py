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


def _stopped_session() -> session_store._WechatDemoSession:
    return session_store._WechatDemoSession(
        session_id="session-test",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        phase=session_store._StorePhase.STOPPED,
    )


@pytest.mark.asyncio
async def test_fail_session_ignores_stopped_session() -> None:
    session = _stopped_session()
    await session_store._fail_session(session, "late failure after stop")
    assert session.phase == session_store._StorePhase.STOPPED
    assert session.error is None


@pytest.mark.asyncio
async def test_set_session_qr_flow_ignores_stopped_session() -> None:
    session = _stopped_session()
    accepted = await session_store._set_session_qr_flow(session, object())
    assert accepted is False
    assert session.qr_flow is None


@pytest.mark.asyncio
async def test_set_session_channel_ignores_stopped_session() -> None:
    session = _stopped_session()
    accepted = await session_store._set_session_channel(session, object())
    assert accepted is False
    assert session.channel_session is None
    assert session.phase == session_store._StorePhase.STOPPED
