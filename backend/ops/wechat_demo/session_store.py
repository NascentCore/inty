"""In-memory WeChat demo sessions (single Ops process; lost on restart)."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from loguru import logger

from backend.ops.schemas.wechat_demo import (
    WechatDemoSessionCreate,
    WechatDemoSessionPhase,
    WechatDemoSessionView,
)


def _ensure_wechat_demo_dependencies() -> None:
    try:
        import gateway.config  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "WeChat demo requires hermes-agent[messaging]; "
            "pip install -r demos/inty_wechat_connector/requirements.txt"
        ) from exc


def _import_wechat_demo_runtime() -> tuple[Any, ...]:
    _ensure_wechat_demo_dependencies()
    from demos.inty_wechat_connector.inty_ws_client import IntyWsConnection
    from demos.inty_wechat_connector.weixin_bridge import (
        WeixinBridgeRunner,
        WeixinCredential,
    )
    from demos.inty_wechat_connector.weixin_qr_flow import WeixinQrFlow
    from hermes_constants import get_hermes_home

    return (
        IntyWsConnection,
        WeixinBridgeRunner,
        WeixinCredential,
        WeixinQrFlow,
        get_hermes_home,
    )


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
    qr_flow: Any = None
    error: str | None = None
    bridge_runner: Any = None
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


async def create_session(body: WechatDemoSessionCreate) -> WechatDemoSessionView:
    _ensure_wechat_demo_dependencies()
    session_id = str(uuid.uuid4())
    session = _WechatDemoSession(
        session_id=session_id,
        inty_api_base_url=body.inty_api_base_url.strip(),
        inty_jwt=body.inty_jwt.strip(),
        agent_id=body.agent_id.strip(),
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
    await _stop_session_tasks(session)
    session.phase = _StorePhase.STOPPED
    return _view(session)


async def _stop_session_tasks(session: _WechatDemoSession) -> None:
    if session.orchestrator_task is not None and not session.orchestrator_task.done():
        session.orchestrator_task.cancel()
        try:
            await session.orchestrator_task
        except asyncio.CancelledError:
            pass
        session.orchestrator_task = None
    if session.bridge_runner is not None:
        await session.bridge_runner.stop()
        session.bridge_runner = None
    if session.bridge_task is not None and not session.bridge_task.done():
        session.bridge_task.cancel()
        try:
            await session.bridge_task
        except asyncio.CancelledError:
            pass
        session.bridge_task = None


async def _run_session_lifecycle(session: _WechatDemoSession) -> None:
    (
        IntyWsConnection,
        WeixinBridgeRunner,
        WeixinCredential,
        WeixinQrFlow,
        get_hermes_home,
    ) = _import_wechat_demo_runtime()
    hermes_home = str(get_hermes_home())
    os.makedirs(hermes_home, exist_ok=True)
    qr_flow = WeixinQrFlow(hermes_home)
    session.qr_flow = qr_flow
    try:
        cred = await qr_flow.run(timeout_seconds=480)
    except asyncio.CancelledError:
        if session.bridge_runner is not None:
            await session.bridge_runner.stop()
        raise
    except Exception as exc:
        logger.exception("wechat_demo QR flow failed session_id={}", session.session_id)
        session.phase = _StorePhase.FAILED
        session.error = str(exc)
        return

    if cred is None:
        session.phase = _StorePhase.FAILED
        if session.error is None:
            session.error = qr_flow.error or "Weixin login failed"
        return

    inty = IntyWsConnection(
        api_base_url=session.inty_api_base_url,
        jwt=session.inty_jwt,
        agent_id=session.agent_id,
    )
    weixin_cred = WeixinCredential(
        account_id=cred["account_id"],
        token=cred["token"],
        base_url=cred.get("base_url") or "https://ilinkai.weixin.qq.com",
    )
    runner = WeixinBridgeRunner(weixin_cred, inty)
    session.bridge_runner = runner
    session.phase = _StorePhase.BRIDGE_RUNNING

    async def _bridge_loop() -> None:
        try:
            await runner.run_until_stopped()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "wechat_demo bridge failed session_id={}", session.session_id
            )
            session.phase = _StorePhase.FAILED
            session.error = str(exc)

    session.bridge_task = asyncio.create_task(
        _bridge_loop(),
        name=f"wechat_demo_bridge_{session.session_id}",
    )
    await session.bridge_task
    if session.phase == _StorePhase.BRIDGE_RUNNING:
        session.phase = _StorePhase.STOPPED
