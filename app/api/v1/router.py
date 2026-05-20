from fastapi import APIRouter

from app.api.constants import API_V1_PREFIX
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
    phone_call,
    report,
    settings,
    subscription,
    text_to_speech,
    users,
    version,
)

api_router = APIRouter(prefix=API_V1_PREFIX)

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(users.router, tags=["users"])

# TODO: Understand the current implementation, which only calls @GET("/api/v1/notifications/")
# The current implementation is also likely insecure, as it expose apis to the internet.
# Instead, we should have an internal service to post push messages to firebase,
# and let firebase push messages to the app. The internal service should be protected by a token.
# TODO: Figure out can we just rely on firebase for push messages?
api_router.include_router(
    notification.router,
    tags=["notification"],
)

api_router.include_router(report.router, tags=["report"])
api_router.include_router(agents.router, tags=["agents", "characters"])
api_router.include_router(chats.router, tags=["chats"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(chat_ws.router, prefix="/chat", tags=["chat"])
api_router.include_router(images.router, tags=["images"])
api_router.include_router(settings.router, tags=["settings"])

api_router.include_router(subscription.router, tags=["subscription"])
api_router.include_router(version.router, tags=["version"])
api_router.include_router(text_to_speech.router, tags=["text_to_speech"])
api_router.include_router(character_themes.router, tags=["character-themes"])
api_router.include_router(live_chat.router, tags=["live-chat"])
api_router.include_router(phone_call.router, tags=["phone-calls"])
