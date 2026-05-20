"""Re-export shared API routers from app (used by Android and evaluation)."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    auth,
    character_themes,
    chat,
    chat_ws,
    chats,
    images,
    live_chat,
    notification,
    report,
    settings,
    subscription,
    text_to_speech,
    users,
    version,
)

shared_router = APIRouter()

shared_router.include_router(auth.router, tags=["auth"])
shared_router.include_router(users.router, tags=["users"])
shared_router.include_router(notification.router, tags=["notification"])
shared_router.include_router(report.router, tags=["report"])
shared_router.include_router(agents.router, tags=["agents", "characters"])
shared_router.include_router(chats.router, tags=["chats"])
shared_router.include_router(chat.router, tags=["chat"])
shared_router.include_router(chat_ws.router, prefix="/chat", tags=["chat"])
shared_router.include_router(images.router, tags=["images"])
shared_router.include_router(settings.router, tags=["settings"])
shared_router.include_router(subscription.router, tags=["subscription"])
shared_router.include_router(version.router, tags=["version"])
shared_router.include_router(text_to_speech.router, tags=["text_to_speech"])
shared_router.include_router(character_themes.router, tags=["character-themes"])
shared_router.include_router(live_chat.router, tags=["live-chat"])
