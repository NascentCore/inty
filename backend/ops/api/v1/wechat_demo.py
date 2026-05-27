"""Ops-only API: WeChat QR login + Inty WS bridge demo (bridge state in Postgres).

Post-scan ``weixin_token`` (iLink ``bot_token``): protocol publishes **no** fixed
validity duration; treat as valid until ``errcode=-14`` on iLink long-poll/send — see
``backend.ops.weixin_channel.ilink_qr_client``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse
from backend.ops.schemas.wechat_demo import (
    WechatDemoSessionCreate,
    WechatDemoSessionView,
)
from backend.ops.wechat_demo import session_store
from backend.ops.wechat_demo.qrcode_png import (
    WECHAT_DEMO_QR_BOX_SIZE,
    qrcode_png_bytes,
)

router = APIRouter(
    prefix="/wechat-demo",
    route_class=LoggerRoute,
    include_in_schema=False,
)


@router.post(
    "/sessions",
    response_model=APIResponse[WechatDemoSessionView],
    summary="Start WeChat demo session (QR login + bridge)",
)
async def create_wechat_demo_session(
    body: WechatDemoSessionCreate,
) -> Any:
    view = await session_store.create_session(body)
    return APIResponse.success(data=view)


@router.get(
    "/sessions/{session_id}",
    response_model=APIResponse[WechatDemoSessionView],
    summary="Poll WeChat demo session status",
)
async def get_wechat_demo_session(session_id: str) -> Any:
    view = await session_store.get_session(session_id)
    if view is None:
        raise HTTPException(status_code=404, detail="session not found")
    return APIResponse.success(data=view)


@router.get(
    "/sessions/{session_id}/qrcode",
    summary="WeChat demo session QR code PNG",
    responses={200: {"content": {"image/png": {}}}},
)
async def get_wechat_demo_session_qrcode(session_id: str) -> Response:
    payload = await session_store.get_session_qrcode_payload(session_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="qrcode not available")
    png = qrcode_png_bytes(payload, WECHAT_DEMO_QR_BOX_SIZE)
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.post(
    "/sessions/{session_id}/stop",
    response_model=APIResponse[WechatDemoSessionView],
    summary="Stop WeChat demo bridge and QR login",
)
async def stop_wechat_demo_session(session_id: str) -> Any:
    view = await session_store.stop_session(session_id)
    if view is None:
        raise HTTPException(status_code=404, detail="session not found")
    return APIResponse.success(data=view)
