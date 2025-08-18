from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    agents,
    auth,
    chats,
    evaluation,
    notification,
    report,
    settings,
    subscription,
    users,
    version,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# TODO: Understand the current implementation, which only calls @GET("/api/v1/notifications/")
# The current implementation is also likely insecure, as it expose apis to the internet.
# Instead, we should have an internal service to post push messages to firebase,
# and let firebase push messages to the app. The internal service should be protected by a token.
# TODO: Figure out can we just rely on firebase for push messages?
api_router.include_router(
    notification.router,
    prefix="/notifications",
    tags=["notification"],
)

api_router.include_router(report.router, prefix="/report", tags=["report"])
api_router.include_router(agents.router, prefix="/ai/agents", tags=["agents"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])

# TODO: Consider remove /resources endpoint.
# api_router.include_router(resources.router, prefix="/resources", tags=["resources"])

api_router.include_router(
    subscription.router, prefix="/subscription", tags=["subscription"]
)

# TODO: Consider remove /admin endpoint, the current implementation is not used.
# It's also highly risky to expose admin apis to the internet.
# Instead, we should have an internal service to manage backend settings.
# api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# TODO: Consider remove /evaluation endpoint.
# This is used for evaluating AI characters, and is not part of the app's runtime.
# Instead, we should have an internal service to evaluate AI characters.
# Still keep the endpoint for now, as it's used for evaluating AI characters.
api_router.include_router(
    evaluation.router,
    prefix="/evaluation",
    tags=["evaluation"],
    include_in_schema=False,
)
api_router.include_router(version.router, prefix="/version", tags=["version"])
