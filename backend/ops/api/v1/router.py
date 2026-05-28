"""Ops API v1 router: evaluation-only endpoints + shared app endpoints."""

from fastapi import APIRouter

from app.api.constants import API_V1_PREFIX

from backend.ops.api.v1 import evaluation, festival_memory, wechat_demo, weixin
from backend.ops.api.v1.shared import shared_router

api_router = APIRouter(prefix=API_V1_PREFIX)

api_router.include_router(shared_router)
api_router.include_router(
    evaluation.router,
    tags=["evaluation"],
    include_in_schema=False,
)
api_router.include_router(
    festival_memory.router,
    tags=["festival-memory"],
    include_in_schema=False,
)
api_router.include_router(
    wechat_demo.router,
    tags=["wechat-demo"],
    include_in_schema=False,
)
api_router.include_router(
    weixin.router,
    tags=["weixin-onboard"],
    include_in_schema=False,
)
