"""WeChat demo sessions: in-memory registry + Postgres-backed bridge resume.

iLink limits: QR phase — ``WeixinQrFlow`` + ``WECHAT_DEMO_QR_LOGIN_POLL_TIMEOUT_SECONDS``
(480s); per-QR ``expired`` refresh (max 3). Bridge phase — ``weixin_token`` until iLink
``errcode=-14`` (re QR); **not** a fixed 14-minute QR validity (do not confuse with -14).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from enum import StrEnum

from hermes_constants import get_hermes_home
from loguru import logger

from backend.ops.schemas.wechat_demo import (
    WechatDemoSessionCreate,
    WechatDemoSessionPhase,
    WechatDemoSessionView,
)
from backend.ops.wechat_demo.session_persistence import (
    PersistedWechatDemoBridge,
    delete_bridge,
    list_bridges,
    record_from_binding_fields,
    upsert_bridge,
)
from backend.ops.weixin_channel.session import (
    WeixinChannelBinding,
    WeixinChannelSession,
)
from backend.ops.weixin_channel.weixin_qr_flow import WeixinQrFlow

# Client-side cap for QR poll loop (matches Hermes / openilink 8 min login budget).
WECHAT_DEMO_QR_LOGIN_POLL_TIMEOUT_SECONDS = 480


class _StorePhase(StrEnum):
    QR_LOGIN = "qr_login"
    BRIDGE_RUNNING = "bridge_running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class _WechatDemoSession:
    session_id: str
    inty_api_base_url: str
    inty_jwt: str
    agent_id: str
    phase: _StorePhase = _StorePhase.QR_LOGIN
    qr_flow: WeixinQrFlow | None = None
    error: str | None = None
    channel_session: WeixinChannelSession | None = None
    orchestrator_task: asyncio.Task[None] | None = None
    bridge_task: asyncio.Task[None] | None = None


_lock = asyncio.Lock()
_sessions: dict[str, _WechatDemoSession] = {}


def _view(session: _WechatDemoSession) -> WechatDemoSessionView:
    qr_phase = None
    qrcode_url = None
    if session.qr_flow is not None:
        qr_phase = session.qr_flow.phase.value
        qrcode_url = session.qr_flow.qrcode_url
    err = session.error
    if err is None and session.qr_flow is not None and session.qr_flow.error:
        err = session.qr_flow.error
    bridge_running = session.phase == _StorePhase.BRIDGE_RUNNING
    return WechatDemoSessionView(
        session_id=session.session_id,
        phase=WechatDemoSessionPhase(session.phase.value),
        qr_phase=qr_phase,
        qrcode_url=qrcode_url,
        error=err,
        bridge_running=bridge_running,
    )


def _hermes_home_str() -> str:
    hermes_home = str(get_hermes_home())
    os.makedirs(hermes_home, exist_ok=True)
    return hermes_home


async def _persist_bridge_session(session: _WechatDemoSession) -> None:
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
    session: _WechatDemoSession,
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


def _binding_from_persisted(record: PersistedWechatDemoBridge) -> WeixinChannelBinding:
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
    session: _WechatDemoSession,
    binding: WeixinChannelBinding,
) -> WeixinChannelSession:
    async def on_binding_peer_updated(_binding: WeixinChannelBinding) -> None:
        await _persist_bridge_session(session)

    return WeixinChannelSession(
        binding=binding,
        on_binding_peer_updated=on_binding_peer_updated,
    )


async def create_session(
    body: WechatDemoSessionCreate,
) -> WechatDemoSessionView:
    session_id = str(uuid.uuid4())
    session = _WechatDemoSession(
        session_id=session_id,
        inty_api_base_url=body.inty_api_base_url,
        inty_jwt=body.inty_jwt,
        agent_id=body.agent_id,
    )
    async with _lock:
        _sessions[session_id] = session
        session.orchestrator_task = asyncio.create_task(
            _run_session_lifecycle(session),
            name=f"wechat_demo_{session_id}",
        )
        return _view(session)


async def get_session(session_id: str) -> WechatDemoSessionView | None:
    async with _lock:
        session = _sessions.get(session_id)
        if session is None:
            return None
        return _view(session)


async def stop_session(session_id: str) -> WechatDemoSessionView | None:
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

    TODO(wechat-demo-bridge-multi-replica): requires a single Ops runner; multiple Pods
    would each restore every row and open duplicate Weixin connections.

    Manual release smoke: ``.cursor/skills/wechat-demo-bridge-restore-smoke/SKILL.md``.
    """
    for record in await list_bridges():
        asyncio.create_task(
            _restore_persisted_session(record),
            name=f"wechat_demo_restore_{record.session_id}",
        )


async def _stop_session_tasks(session: _WechatDemoSession) -> None:
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
    session: _WechatDemoSession,
    qr_flow: WeixinQrFlow,
) -> bool:
    async with _lock:
        if session.phase == _StorePhase.STOPPED:
            return False
        session.qr_flow = qr_flow
        return True


async def _fail_session(session: _WechatDemoSession, error: str) -> None:
    async with _lock:
        if session.phase == _StorePhase.STOPPED:
            return
        session.phase = _StorePhase.FAILED
        session.error = error
    await _clear_persisted_bridge(session.session_id)


async def _set_session_channel(
    session: _WechatDemoSession,
    channel_session: WeixinChannelSession,
) -> bool:
    async with _lock:
        if session.phase == _StorePhase.STOPPED:
            return False
        session.channel_session = channel_session
        session.phase = _StorePhase.BRIDGE_RUNNING
        return True


async def _set_session_bridge_task(
    session: _WechatDemoSession,
    bridge_task: asyncio.Task[None],
) -> bool:
    async with _lock:
        if session.phase == _StorePhase.STOPPED:
            return False
        session.bridge_task = bridge_task
        return True


async def _mark_session_stopped_after_bridge(
    session: _WechatDemoSession,
) -> None:
    async with _lock:
        if session.phase == _StorePhase.BRIDGE_RUNNING:
            session.phase = _StorePhase.STOPPED
    await _clear_persisted_bridge(session.session_id)


async def _run_bridge_until_stopped(
    session: _WechatDemoSession,
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
                "wechat_demo bridge failed session_id={}", session.session_id
            )
            await _fail_session(session, str(exc))

    bridge_task = asyncio.create_task(
        _bridge_loop(),
        name=f"wechat_demo_bridge_{session.session_id}",
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


async def _restore_persisted_session(
    record: PersistedWechatDemoBridge,
) -> None:
    """Reattach bridge; register in-memory session before channel.start (poll 404 window)."""
    session = _WechatDemoSession(
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
            "wechat_demo restore channel start failed session_id={}",
            record.session_id,
        )
        async with _lock:
            _sessions.pop(record.session_id, None)
        await delete_bridge(record.session_id)
        return
    await _run_bridge_until_stopped(session, channel)


async def _run_session_lifecycle(session: _WechatDemoSession) -> None:
    hermes_home = _hermes_home_str()
    qr_flow = WeixinQrFlow(hermes_home)
    if not await _set_session_qr_flow(session, qr_flow):
        return
    try:
        cred = await qr_flow.run(
            timeout_seconds=WECHAT_DEMO_QR_LOGIN_POLL_TIMEOUT_SECONDS,
        )
    except asyncio.CancelledError:
        async with _lock:
            channel_session = session.channel_session
        if channel_session is not None:
            await channel_session.stop()
        raise
    except Exception as exc:
        logger.exception(
            "wechat_demo QR flow failed session_id={}", session.session_id
        )
        await _fail_session(session, str(exc))
        return

    if cred is None:
        await _fail_session(
            session,
            qr_flow.error or "Weixin login failed",
        )
        return

    binding = _binding_from_qr_cred(session, cred)
    channel = _channel_for_session(session, binding)
    try:
        await channel.start()
    except Exception as exc:
        logger.exception(
            "wechat_demo channel start failed session_id={}", session.session_id
        )
        await _fail_session(session, str(exc))
        return
    await _run_bridge_until_stopped(session, channel)
