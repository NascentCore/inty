from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    notification,
    users,
    agents,
    chats,
    settings,
    report,
    subscription,
    evaluation,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(
    notification.router, prefix="/notifications", tags=["notification"]
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
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
