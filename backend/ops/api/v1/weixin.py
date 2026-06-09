"""Ops-only API: Weixin onboard (QR login → provision user + agent + bridge).

QR 登录成功之后、在 Ops 里长期运行的 微信 ↔ Inty companion 消息中继
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse
from backend.ops.schemas.weixin_session import (
    WeixinOnboardSessionCreate,
    WeixinSessionView,
)
from backend.ops.weixin_session import session_store
from backend.ops.weixin_session.session_store import OnboardQrReadyTimeoutError

router = APIRouter(
    prefix="/weixin",
    route_class=LoggerRoute,
    include_in_schema=False,
)


@router.post(
    "/sessions",
    response_model=APIResponse[WeixinSessionView],
    summary="Start Weixin onboard session (QR login + auto provision)",
)
async def create_weixin_onboard_session(
    body: WeixinOnboardSessionCreate,
) -> Any:
    try:
        view = await session_store.create_onboard_session(body)
    except OnboardQrReadyTimeoutError:
        raise HTTPException(
            status_code=504, detail="QR ready timeout"
        ) from None
    return APIResponse.success(data=view)


@router.get(
    "/sessions/{session_id}",
    response_model=APIResponse[WeixinSessionView],
    summary="Poll Weixin onboard session status",
)
async def get_weixin_onboard_session(session_id: str) -> Any:
    view = await session_store.get_session(session_id)
    if view is None:
        raise HTTPException(status_code=404, detail="session not found")
    return APIResponse.success(data=view)


@router.post(
    "/sessions/{session_id}/stop",
    response_model=APIResponse[WeixinSessionView],
    summary="Stop Weixin onboard bridge and QR login",
)
async def stop_weixin_onboard_session(session_id: str) -> Any:
    view = await session_store.stop_session(session_id)
    if view is None:
        raise HTTPException(status_code=404, detail="session not found")
    return APIResponse.success(data=view)
