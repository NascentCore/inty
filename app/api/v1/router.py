from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    auth,
    chat,
    chats,
    evaluation,
    images,
    notification,
    report,
    settings,
    subscription,
    text_to_speech,
    users,
    version,
)
from app.api.constants import API_V1_PREFIX

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
api_router.include_router(images.router, tags=["images"])
api_router.include_router(settings.router, tags=["settings"])

api_router.include_router(subscription.router, tags=["subscription"])

# TODO: Consider remove /evaluation endpoint.
# This is used for evaluating AI characters, and is not part of the app's runtime.
# Instead, we should have an internal service to evaluate AI characters.
# Still keep the endpoint for now, as it's used for evaluating AI characters.
api_router.include_router(
    evaluation.router,
    tags=["evaluation"],
    include_in_schema=False,
)
api_router.include_router(version.router, tags=["version"])
api_router.include_router(text_to_speech.router, tags=["text_to_speech"])
