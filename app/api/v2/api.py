from fastapi import APIRouter

from app.api.v2.endpoints import chats

api_router = APIRouter(prefix="/api/v2")

api_router.include_router(chats.router, tags=["chats"])
