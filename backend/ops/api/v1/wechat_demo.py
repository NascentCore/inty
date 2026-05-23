"""Ops-only API for the WeChat self-service demo.

The API starts a temporary QR login session, exposes polling state for the
browser page, and stops the bridge on request. It is hidden from OpenAPI
because it is an internal demo surface, not a stable product contract.
Missing WeChat bridge dependencies are reported as unavailable so Ops can
still run other evaluation and shared APIs without the demo extra installed.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse
from backend.ops.schemas.wechat_demo import (
    WechatDemoSessionCreate,
    WechatDemoSessionView,
)
from backend.ops.wechat_demo import session_store

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
    try:
        view = await session_store.create_session(body)
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "WeChat demo requires hermes-agent[messaging]; "
                f"install demos/inty_wechat_connector/requirements.txt ({exc})"
            ),
        ) from exc
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
