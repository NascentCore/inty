"""Weixin onboard sessions: in-memory registry + Postgres-backed bridge resume."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from enum import StrEnum

from loguru import logger

from app.db.session import AsyncSessionLocal
from app.services.agentic_channel.companion_bonds import (
    has_active_companion_bond_for_agent,
)
from backend.ops.schemas.weixin_session import (
    WeixinOnboardSessionCreate,
    WeixinSessionPhase,
    WeixinSessionView,
)
from backend.ops.weixin_channel.ilink_qr_client import (
    ILINK_SESSION_EXPIRED_USER_MESSAGE,
)
from backend.ops.weixin_channel.session import (
    WeixinChannelBinding,
    WeixinChannelSession,
)
from backend.ops.weixin_channel.weixin_qr_flow import WeixinQrFlow
from backend.ops.weixin_onboard.provision import provision_inty_for_ilink_user
from backend.ops.weixin_session.session_persistence import (
    PersistedWeixinBridge,
    delete_bridge,
    list_bridges,
    record_from_binding_fields,
    upsert_bridge,
)

# Client-side cap for QR poll loop (matches Hermes / openilink 8 min login budget).
WEIXIN_QR_LOGIN_POLL_TIMEOUT_SECONDS = 480

# Onboard POST blocks until first qrcode_url (not the full 480s login window).
WEIXIN_ONBOARD_QR_READY_TIMEOUT_SECONDS = 60


class OnboardQrReadyTimeoutError(Exception):
    """First iLink QR was not ready before ``WEIXIN_ONBOARD_QR_READY_TIMEOUT_SECONDS``."""


class _StorePhase(StrEnum):
    QR_LOGIN = "qr_login"
    BRIDGE_RUNNING = "bridge_running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class _WeixinSession:
    session_id: str
    inty_api_base_url: str
    inty_jwt: str
    agent_id: str
    onboard: bool = False
    is_new_user: bool | None = None
    ilink_user_id: str | None = None
    qrcode_ready: asyncio.Event | None = None
    phase: _StorePhase = _StorePhase.QR_LOGIN
    qr_flow: WeixinQrFlow | None = None
    error: str | None = None
    channel_session: WeixinChannelSession | None = None
    orchestrator_task: asyncio.Task[None] | None = None
    bridge_task: asyncio.Task[None] | None = None


_lock = asyncio.Lock()
_sessions: dict[str, _WeixinSession] = {}
# Strong refs: bare create_task() is weak-held by the loop and may be GC'd mid-restore.
_restore_tasks: set[asyncio.Task[None]] = set()


def _phase_blocks_lifecycle(phase: _StorePhase) -> bool:
    return phase in (_StorePhase.STOPPED, _StorePhase.FAILED)


async def _session_lifecycle_may_continue(session: _WeixinSession) -> bool:
    async with _lock:
        return not _phase_blocks_lifecycle(session.phase)


def _view(session: _WeixinSession) -> WeixinSessionView:
    qr_phase = None
    qrcode_url = None
    if session.qr_flow is not None:
        qr_phase = session.qr_flow.phase.value
        qrcode_url = session.qr_flow.qrcode_url
    err = session.error
    if err is None and session.qr_flow is not None and session.qr_flow.error:
        err = session.qr_flow.error
    bridge_running = session.phase == _StorePhase.BRIDGE_RUNNING
    agent_id = None
    is_new_user = None
    if session.onboard:
        if session.agent_id:
            agent_id = session.agent_id
        is_new_user = session.is_new_user
    return WeixinSessionView(
        session_id=session.session_id,
        phase=WeixinSessionPhase(session.phase.value),
        qr_phase=qr_phase,
        qrcode_url=qrcode_url,
        error=err,
        bridge_running=bridge_running,
        agent_id=agent_id,
        is_new_user=is_new_user,
    )


async def _persist_bridge_session(session: _WeixinSession) -> None:
    channel = session.channel_session
    assert channel is not None
    binding = channel.binding
    record = record_from_binding_fields(
        session_id=session.session_id,
        inty_api_base_url=session.inty_api_base_url,
        inty_jwt=session.inty_jwt,
        agent_id=session.agent_id,
        weixin_account_id=binding.weixin_account_id,
        weixin_token=binding.weixin_token,
        weixin_base_url=binding.weixin_base_url,
        last_peer_id=binding.last_peer_id,
        last_peer_seen_at=binding.last_peer_seen_at,
    )
    await upsert_bridge(record)


async def _clear_persisted_bridge(session_id: str) -> None:
    await delete_bridge(session_id)


def _binding_from_qr_cred(
    session: _WeixinSession,
    cred: dict[str, str],
) -> WeixinChannelBinding:
    return WeixinChannelBinding(
        user_id=session.session_id,
        agent_id=session.agent_id,
        inty_api_base_url=session.inty_api_base_url,
        inty_jwt=session.inty_jwt,
        weixin_account_id=cred["account_id"],
        weixin_token=cred["token"],
        weixin_base_url=cred.get("base_url") or "https://ilinkai.weixin.qq.com",
    )


def _binding_from_persisted(
    record: PersistedWeixinBridge,
) -> WeixinChannelBinding:
    return WeixinChannelBinding(
        user_id=record.session_id,
        agent_id=record.agent_id,
        inty_api_base_url=record.inty_api_base_url,
        inty_jwt=record.inty_jwt,
        weixin_account_id=record.weixin_account_id,
        weixin_token=record.weixin_token,
        weixin_base_url=record.weixin_base_url,
        last_peer_id=record.last_peer_id,
        last_peer_seen_at=record.last_peer_seen_at,
    )


def _channel_for_session(
    session: _WeixinSession,
    binding: WeixinChannelBinding,
) -> WeixinChannelSession:
    async def on_binding_peer_updated(_binding: WeixinChannelBinding) -> None:
        await _persist_bridge_session(session)

    async def on_ilink_session_expired() -> None:
        await fail_weixin_ilink_session_expired(session.session_id)

    return WeixinChannelSession(
        binding=binding,
        on_binding_peer_updated=on_binding_peer_updated,
        on_ilink_session_expired=on_ilink_session_expired,
    )


async def create_onboard_session(
    body: WeixinOnboardSessionCreate,
) -> WeixinSessionView:
    session_id = str(uuid.uuid4())
    session = _WeixinSession(
        session_id=session_id,
        inty_api_base_url=body.inty_api_base_url,
        inty_jwt="",
        agent_id="",
        onboard=True,
        qrcode_ready=asyncio.Event(),
    )
    async with _lock:
        _sessions[session_id] = session
        session.orchestrator_task = asyncio.create_task(
            _run_session_lifecycle(session),
            name=f"weixin_onboard_{session_id}",
        )
    assert session.qrcode_ready is not None
    try:
        await asyncio.wait_for(
            session.qrcode_ready.wait(),
            timeout=WEIXIN_ONBOARD_QR_READY_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await _fail_session(session, "QR ready timeout")
        raise OnboardQrReadyTimeoutError("QR ready timeout") from None
    async with _lock:
        return _view(session)


async def fail_weixin_ilink_session_expired(session_id: str) -> None:
    """Tear down bridge after iLink ``errcode=-14`` (idempotent)."""
    assert session_id != ""
    async with _lock:
        session = _sessions.get(session_id)
        if session is None:
            return
        if _phase_blocks_lifecycle(session.phase):
            return
    await _fail_session(session, ILINK_SESSION_EXPIRED_USER_MESSAGE)


async def get_session(session_id: str) -> WeixinSessionView | None:
    async with _lock:
        session = _sessions.get(session_id)
        if session is None:
            return None
        return _view(session)


async def stop_session(session_id: str) -> WeixinSessionView | None:
    async with _lock:
        session = _sessions.get(session_id)
        if session is None:
            return None
        session.phase = _StorePhase.STOPPED
    await _stop_session_tasks(session)
    await _clear_persisted_bridge(session_id)
    async with _lock:
        return _view(session)


async def restore_persisted_sessions() -> None:
    """Reload Postgres-backed bridges after Ops restart (no QR).

    TODO(weixin-bridge-multi-replica): requires a single Ops runner; multiple Pods
    would each restore every row and open duplicate Weixin connections.

    Manual release smoke: ``.cursor/skills/weixin-bridge-restore-smoke/SKILL.md``.
    """
    for record in await list_bridges():
        task = asyncio.create_task(
            _restore_persisted_session(record),
            name=f"weixin_restore_{record.session_id}",
        )
        _restore_tasks.add(task)
        task.add_done_callback(_restore_tasks.discard)


async def _stop_session_tasks(session: _WeixinSession) -> None:
    async with _lock:
        orchestrator_task = session.orchestrator_task
        channel_session = session.channel_session
        bridge_task = session.bridge_task
    if orchestrator_task is not None and not orchestrator_task.done():
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass
    if channel_session is not None:
        await channel_session.stop()
    if bridge_task is not None and not bridge_task.done():
        bridge_task.cancel()
        try:
            await bridge_task
        except asyncio.CancelledError:
            pass
    async with _lock:
        if session.orchestrator_task is orchestrator_task:
            session.orchestrator_task = None
        if session.channel_session is channel_session:
            session.channel_session = None
        if session.bridge_task is bridge_task:
            session.bridge_task = None


async def _set_session_qr_flow(
    session: _WeixinSession,
    qr_flow: WeixinQrFlow,
) -> bool:
    async with _lock:
        if _phase_blocks_lifecycle(session.phase):
            return False
        session.qr_flow = qr_flow
        return True


async def _fail_session(session: _WeixinSession, error: str) -> None:
    orchestrator_task: asyncio.Task[None] | None = None
    channel_session: WeixinChannelSession | None = None
    bridge_task: asyncio.Task[None] | None = None
    async with _lock:
        if _phase_blocks_lifecycle(session.phase):
            return
        session.phase = _StorePhase.FAILED
        session.error = error
        ready = session.qrcode_ready
        if ready is not None and not ready.is_set():
            ready.set()
        orchestrator_task = session.orchestrator_task
        channel_session = session.channel_session
        bridge_task = session.bridge_task
    await _clear_persisted_bridge(session.session_id)
    current = asyncio.current_task()
    orchestrator_to_stop = (
        orchestrator_task is not None
        and not orchestrator_task.done()
        and orchestrator_task is not current
    )
    bridge_to_stop = channel_session is not None or (
        bridge_task is not None and not bridge_task.done()
    )
    if orchestrator_to_stop or bridge_to_stop:
        await _stop_session_tasks(session)


async def _set_session_channel(
    session: _WeixinSession,
    channel_session: WeixinChannelSession,
) -> bool:
    async with _lock:
        if _phase_blocks_lifecycle(session.phase):
            return False
        session.channel_session = channel_session
        session.phase = _StorePhase.BRIDGE_RUNNING
        return True


async def _set_session_bridge_task(
    session: _WeixinSession,
    bridge_task: asyncio.Task[None],
) -> bool:
    async with _lock:
        if _phase_blocks_lifecycle(session.phase):
            return False
        session.bridge_task = bridge_task
        return True


async def _mark_session_stopped_after_bridge(
    session: _WeixinSession,
) -> None:
    async with _lock:
        if session.phase == _StorePhase.BRIDGE_RUNNING:
            session.phase = _StorePhase.STOPPED
    await _clear_persisted_bridge(session.session_id)


async def _run_bridge_until_stopped(
    session: _WeixinSession,
    channel: WeixinChannelSession,
) -> None:
    if not await _set_session_channel(session, channel):
        await channel.stop()
        return
    await _persist_bridge_session(session)

    async def _bridge_loop() -> None:
        try:
            await channel.run_until_stopped()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "weixin bridge failed session_id={}", session.session_id
            )
            await _fail_session(session, str(exc))

    bridge_task = asyncio.create_task(
        _bridge_loop(),
        name=f"weixin_bridge_{session.session_id}",
    )
    if not await _set_session_bridge_task(session, bridge_task):
        bridge_task.cancel()
        await _clear_persisted_bridge(session.session_id)
        try:
            await bridge_task
        except asyncio.CancelledError:
            pass
        return
    await bridge_task
    await _mark_session_stopped_after_bridge(session)


def _onboard_same_weixin_identity(
    other: _WeixinSession,
    ilink_user_id: str,
    weixin_account_id: str,
) -> bool:
    assert ilink_user_id != ""
    assert weixin_account_id != ""
    if other.ilink_user_id == ilink_user_id:
        return True
    channel = other.channel_session
    if channel is not None:
        if channel.binding.weixin_account_id == weixin_account_id:
            return True
    return False


async def _stop_other_onboard_sessions_for_same_weixin(
    current: _WeixinSession,
    cred: dict[str, str],
) -> None:
    """After new bridge started: stop prior onboard sessions for this WeChat identity only."""
    assert current.onboard
    ilink_user_id = current.ilink_user_id
    assert ilink_user_id is not None
    weixin_account_id = cred["account_id"]
    async with _lock:
        other_ids = [
            sid
            for sid, other in _sessions.items()
            if other.onboard
            and sid != current.session_id
            and other.phase
            in (_StorePhase.QR_LOGIN, _StorePhase.BRIDGE_RUNNING)
            and _onboard_same_weixin_identity(
                other,
                ilink_user_id,
                weixin_account_id,
            )
        ]
    for sid in other_ids:
        await stop_session(sid)


async def _signal_qrcode_ready_while_running(
    session: _WeixinSession,
    qr_flow: WeixinQrFlow,
    qr_task: asyncio.Task[dict[str, str] | None],
) -> dict[str, str] | None:
    ready = session.qrcode_ready
    while not qr_task.done():
        if ready is not None and qr_flow.qrcode_url and not ready.is_set():
            ready.set()
        await asyncio.sleep(0.05)
    if ready is not None and qr_flow.qrcode_url and not ready.is_set():
        ready.set()
    return await qr_task


async def _restore_persisted_session(
    record: PersistedWeixinBridge,
) -> None:
    """Reattach bridge; register in-memory session before channel.start (poll 404 window)."""
    # TODO(shared-companion-provisioning): #3697 — move ACTIVE-bond restore filtering
    # into shared agent_channel restore service (parent epic #3491).
    async with AsyncSessionLocal() as db:
        bond_active = await has_active_companion_bond_for_agent(
            db,
            record.agent_id,
        )
    if not bond_active:
        logger.info(
            "weixin restore skipped inactive bond session_id={} agent_id={}",
            record.session_id,
            record.agent_id,
        )
        await delete_bridge(record.session_id)
        return
    session = _WeixinSession(
        session_id=record.session_id,
        inty_api_base_url=record.inty_api_base_url,
        inty_jwt=record.inty_jwt,
        agent_id=record.agent_id,
    )
    async with _lock:
        if record.session_id in _sessions:
            return
        _sessions[record.session_id] = session
    binding = _binding_from_persisted(record)
    channel = _channel_for_session(session, binding)
    try:
        await channel.start()
    except Exception:
        logger.exception(
            "weixin restore channel start failed session_id={}",
            record.session_id,
        )
        async with _lock:
            _sessions.pop(record.session_id, None)
        await delete_bridge(record.session_id)
        return
    await _run_bridge_until_stopped(session, channel)


async def _run_session_lifecycle(session: _WeixinSession) -> None:
    qr_flow = WeixinQrFlow()
    if not await _set_session_qr_flow(session, qr_flow):
        return
    qr_task = asyncio.create_task(
        qr_flow.run(timeout_seconds=WEIXIN_QR_LOGIN_POLL_TIMEOUT_SECONDS),
        name=f"weixin_qr_{session.session_id}",
    )
    try:
        cred = await _signal_qrcode_ready_while_running(
            session, qr_flow, qr_task
        )
    except asyncio.CancelledError:
        if not qr_task.done():
            qr_task.cancel()
            try:
                await qr_task
            except asyncio.CancelledError:
                pass
        async with _lock:
            channel_session = session.channel_session
        if channel_session is not None:
            await channel_session.stop()
        raise
    except Exception as exc:
        logger.exception(
            "weixin QR flow failed session_id={}", session.session_id
        )
        await _fail_session(session, str(exc))
        return

    if cred is None:
        await _fail_session(
            session,
            qr_flow.error or "Weixin login failed",
        )
        return

    if not await _session_lifecycle_may_continue(session):
        return

    # TODO(weixin-onboard-jwt-delivery): JWT for bridge only; client must not receive via poll.
    ilink_user_id = str(cred.get("user_id") or "")
    if not ilink_user_id:
        await _fail_session(session, "confirmed but ilink_user_id missing")
        return
    try:
        provision = await provision_inty_for_ilink_user(
            ilink_user_id=ilink_user_id,
        )
    except Exception as exc:
        logger.exception(
            "weixin onboard provision failed session_id={}",
            session.session_id,
        )
        await _fail_session(session, str(exc))
        return
    session.ilink_user_id = ilink_user_id
    session.inty_jwt = provision.jwt
    session.agent_id = provision.agent_id
    session.is_new_user = provision.is_new_user

    if not await _session_lifecycle_may_continue(session):
        return

    binding = _binding_from_qr_cred(session, cred)
    channel = _channel_for_session(session, binding)
    try:
        await channel.start()
    except Exception as exc:
        logger.exception(
            "weixin channel start failed session_id={}", session.session_id
        )
        await _fail_session(session, str(exc))
        return
    await _stop_other_onboard_sessions_for_same_weixin(session, cred)
    await _run_bridge_until_stopped(session, channel)
