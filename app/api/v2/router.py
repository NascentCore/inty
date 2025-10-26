from fastapi import APIRouter

from app.api.v2.endpoints import chat
from app.api.constants import API_V2_PREFIX

api_v2_router = APIRouter(prefix=API_V2_PREFIX)

api_v2_router.include_router(chat.router, tags=["chat"])
