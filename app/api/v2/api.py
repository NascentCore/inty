from fastapi import APIRouter

from app.api.v2.endpoints import chat

api_router = APIRouter(prefix="/api/v2")

api_router.include_router(chat.router, tags=["chats"])
