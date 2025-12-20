from fastapi import APIRouter

from app.api.v2.endpoints import agents, chat, chat_ws
from app.api.constants import API_V2_PREFIX

api_v2_router = APIRouter(prefix=API_V2_PREFIX)

api_v2_router.include_router(chat.router, tags=["chat"])
api_v2_router.include_router(chat_ws.router, tags=["chat"])
api_v2_router.include_router(agents.router, tags=["agents"])
