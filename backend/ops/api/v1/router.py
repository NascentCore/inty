"""Ops API v1 router: evaluation-only endpoints + shared app endpoints."""

from fastapi import APIRouter

from app.api.constants import API_V1_PREFIX

from app.core.config import global_config_loaded_from_config_yaml

from backend.ops.api.v1 import (
    agent_channel,
    evaluation,
    festival_memory,
    telegram,
    telegram_demo,
    weixin,
)
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
    weixin.router,
    tags=["weixin-onboard"],
    include_in_schema=False,
)
api_router.include_router(
    telegram.router,
    tags=["telegram-onboard"],
    include_in_schema=False,
)
if global_config_loaded_from_config_yaml.app.debug:
    api_router.include_router(
        telegram_demo.router,
        tags=["telegram-demo"],
        include_in_schema=False,
    )
api_router.include_router(
    agent_channel.router,
    tags=["agent-channel"],
    include_in_schema=False,
)
