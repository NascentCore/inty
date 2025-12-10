# CREATED_BY_AGENT
"""
IntyEval API v1 路由注册
"""

from fastapi import APIRouter

from eval_app.api.v1.endpoints import (
    agents,
    character_themes,
    chat,
    chats,
    evaluation,
    images,
    text_to_speech,
    users,
)
from app.api.constants import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)

# 注册 evaluation 路由（主要功能）
api_router.include_router(
    evaluation.router,
    tags=["evaluation"],
    include_in_schema=True,
)

# 注册共享端点路由（evaluation 前端也需要使用）
api_router.include_router(agents.router, tags=["agents", "characters"])
api_router.include_router(chats.router, tags=["chats"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(images.router, tags=["images"])
api_router.include_router(text_to_speech.router, tags=["text_to_speech"])
api_router.include_router(character_themes.router, tags=["character-themes"])
api_router.include_router(users.router, tags=["users"])

