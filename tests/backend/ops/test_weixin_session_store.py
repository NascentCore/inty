"""Regression tests for Ops Weixin session state handling."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from backend.ops.schemas.weixin_session import (
    WeixinOnboardSessionCreate,
    WeixinSessionView,
)
from backend.ops.weixin_session import session_store
from backend.ops.weixin_channel.ilink_qr_client import (
    ILINK_SESSION_EXPIRED_USER_MESSAGE,
)
from backend.ops.weixin_channel.session import (
    WeixinChannelBinding,
    WeixinChannelSession,
)
from backend.ops.weixin_channel.weixin_qr_flow import WeixinQrFlow
from app.db.session import async_engine


def test_onboard_session_create_rejects_whitespace_api_base() -> None:
    with pytest.raises(ValidationError):
        WeixinOnboardSessionCreate(inty_api_base_url="   ")


def test_session_view_has_no_jwt_field() -> None:
    assert "inty_jwt" not in WeixinSessionView.model_fields


def test_view_onboard_session_exposes_provision_fields() -> None:
    session = session_store._WeixinSession(
        session_id="session-onboard",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt-internal",
        agent_id="agent-onboard",
        onboard=True,
        is_new_user=True,
        phase=session_store._StorePhase.BRIDGE_RUNNING,
    )
    view = session_store._view(session)
    assert view.agent_id == "agent-onboard"
    assert view.is_new_user is True
    assert view.bridge_running is True


def _stopped_session() -> session_store._WeixinSession:
    return session_store._WeixinSession(
        session_id="session-test",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        phase=session_store._StorePhase.STOPPED,
    )


def _failed_session() -> session_store._WeixinSession:
    return session_store._WeixinSession(
        session_id="session-failed",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        phase=session_store._StorePhase.FAILED,
        error="already failed",
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


@pytest.mark.asyncio
async def test_set_session_qr_flow_ignores_failed_session() -> None:
    session = _failed_session()
    accepted = await session_store._set_session_qr_flow(session, object())
    assert accepted is False
    assert session.qr_flow is None


@pytest.mark.asyncio
async def test_set_session_channel_ignores_failed_session() -> None:
    session = _failed_session()
    accepted = await session_store._set_session_channel(session, object())
    assert accepted is False
    assert session.channel_session is None
    assert session.phase == session_store._StorePhase.FAILED
    assert session.error == "already failed"


async def _noop_ilink_session_expired() -> None:
    pass


class _RecordingChannel:
    """Restore-path stand-in: records ``stop()`` without Hermes / orchestrator."""

    def __init__(self) -> None:
        self.stop_called = False

    async def stop(self) -> None:
        self.stop_called = True


@pytest.mark.asyncio
async def test_fail_weixin_ilink_session_expired_marks_failed() -> None:
    await async_engine.dispose()
    session = session_store._WeixinSession(
        session_id="session-ilink-expired",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        phase=session_store._StorePhase.BRIDGE_RUNNING,
    )
    async with session_store._lock:
        session_store._sessions["session-ilink-expired"] = session
    await session_store.fail_weixin_ilink_session_expired(
        "session-ilink-expired"
    )
    assert session.phase == session_store._StorePhase.FAILED
    assert session.error == ILINK_SESSION_EXPIRED_USER_MESSAGE
    async with session_store._lock:
        session_store._sessions.pop("session-ilink-expired", None)


@pytest.mark.asyncio
async def test_fail_weixin_ilink_session_expired_stops_restore_like_channel() -> (
    None
):
    await async_engine.dispose()
    channel = _RecordingChannel()
    session_id = "session-restore-like-expired"
    bridge_task = asyncio.create_task(asyncio.Event().wait())

    session = session_store._WeixinSession(
        session_id=session_id,
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        phase=session_store._StorePhase.BRIDGE_RUNNING,
        channel_session=channel,  # type: ignore[arg-type]
        bridge_task=bridge_task,
    )
    async with session_store._lock:
        session_store._sessions[session_id] = session
    await session_store.fail_weixin_ilink_session_expired(session_id)
    assert channel.stop_called
    assert session.phase == session_store._StorePhase.FAILED
    assert session.error == ILINK_SESSION_EXPIRED_USER_MESSAGE
    assert session.channel_session is None
    assert bridge_task.done()
    async with session_store._lock:
        session_store._sessions.pop(session_id, None)


@pytest.mark.asyncio
async def test_fail_weixin_ilink_session_expired_idempotent_on_stopped() -> (
    None
):
    session = _stopped_session()
    async with session_store._lock:
        session_store._sessions[session.session_id] = session
    await session_store.fail_weixin_ilink_session_expired(session.session_id)
    assert session.phase == session_store._StorePhase.STOPPED
    assert session.error is None
    async with session_store._lock:
        session_store._sessions.pop(session.session_id, None)


def test_onboard_same_weixin_identity_matches_ilink_user_id() -> None:
    other = session_store._WeixinSession(
        session_id="old",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        onboard=True,
        ilink_user_id="ilink-1",
    )
    assert session_store._onboard_same_weixin_identity(
        other,
        "ilink-1",
        "wx-acc-other",
    )


def test_onboard_same_weixin_identity_matches_bridge_account_id() -> None:
    binding = WeixinChannelBinding(
        user_id="old",
        agent_id="agent",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        weixin_account_id="wx-acc-9",
        weixin_token="tok",
        weixin_base_url="https://ilinkai.weixin.qq.com",
    )
    channel = WeixinChannelSession(
        binding=binding,
        on_binding_peer_updated=None,
        on_ilink_session_expired=_noop_ilink_session_expired,
    )
    other = session_store._WeixinSession(
        session_id="old",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        onboard=True,
        channel_session=channel,
    )
    assert session_store._onboard_same_weixin_identity(
        other,
        "ilink-new",
        "wx-acc-9",
    )


def test_onboard_same_weixin_identity_rejects_different_user() -> None:
    other = session_store._WeixinSession(
        session_id="other-user",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        agent_id="agent",
        onboard=True,
        ilink_user_id="ilink-b",
    )
    assert not session_store._onboard_same_weixin_identity(
        other,
        "ilink-a",
        "wx-acc-x",
    )


@pytest.mark.asyncio
async def test_fail_session_sets_qrcode_ready_event() -> None:
    await async_engine.dispose()
    session = session_store._WeixinSession(
        session_id="session-ready",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="",
        agent_id="",
        onboard=True,
        qrcode_ready=asyncio.Event(),
    )
    await session_store._fail_session(session, "fetch failed")
    assert session.qrcode_ready is not None
    assert session.qrcode_ready.is_set()


@pytest.mark.asyncio
async def test_signal_qrcode_ready_while_running_sets_event() -> None:
    session = session_store._WeixinSession(
        session_id="session-signal",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="",
        agent_id="",
        onboard=True,
        qrcode_ready=asyncio.Event(),
    )
    qr_flow = WeixinQrFlow()
    qr_flow.qrcode_url = "https://qr.example/ready"

    async def slow_run() -> None:
        await asyncio.sleep(0.1)

    qr_task = asyncio.create_task(slow_run())
    await session_store._signal_qrcode_ready_while_running(
        session, qr_flow, qr_task
    )
    assert session.qrcode_ready is not None
    assert session.qrcode_ready.is_set()


@pytest.mark.asyncio
async def test_stop_other_onboard_sessions_only_same_weixin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stopped: list[str] = []

    async def fake_stop(session_id: str) -> None:
        stopped.append(session_id)

    monkeypatch.setattr(session_store, "stop_session", fake_stop)

    current = session_store._WeixinSession(
        session_id="current",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt-new",
        agent_id="agent-new",
        onboard=True,
        ilink_user_id="ilink-a",
        phase=session_store._StorePhase.BRIDGE_RUNNING,
    )
    same_user = session_store._WeixinSession(
        session_id="same-user-old",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt-old",
        agent_id="agent-old",
        onboard=True,
        ilink_user_id="ilink-a",
        phase=session_store._StorePhase.BRIDGE_RUNNING,
    )
    other_user = session_store._WeixinSession(
        session_id="other-user",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt-b",
        agent_id="agent-b",
        onboard=True,
        ilink_user_id="ilink-b",
        phase=session_store._StorePhase.BRIDGE_RUNNING,
    )

    async with session_store._lock:
        session_store._sessions.clear()
        session_store._sessions["current"] = current
        session_store._sessions["same-user-old"] = same_user
        session_store._sessions["other-user"] = other_user

    cred = {
        "account_id": "wx-acc-1",
        "token": "tok",
        "base_url": "https://ilinkai.weixin.qq.com",
        "user_id": "ilink-a",
    }
    await session_store._stop_other_onboard_sessions_for_same_weixin(
        current, cred
    )

    assert stopped == ["same-user-old"]

    async with session_store._lock:
        session_store._sessions.clear()


@pytest.mark.asyncio
async def test_fail_session_cancels_orchestrator_when_called_externally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def noop_clear_persisted_bridge(session_id: str) -> None:
        del session_id

    monkeypatch.setattr(
        session_store,
        "_clear_persisted_bridge",
        noop_clear_persisted_bridge,
    )

    async def fake_orchestrator() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    session = session_store._WeixinSession(
        session_id="session-cancel",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="",
        agent_id="",
        onboard=True,
    )
    orchestrator = asyncio.create_task(fake_orchestrator())
    session.orchestrator_task = orchestrator
    await started.wait()
    await session_store._fail_session(session, "external fail")
    assert cancelled.is_set()
    assert orchestrator.done()
    assert session.phase == session_store._StorePhase.FAILED
    assert session.error == "external fail"
