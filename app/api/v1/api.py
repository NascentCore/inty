from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, agents, chats, messages, settings, resources
from app.api.v1 import verification_code

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(agents.router, prefix="/ai/agents", tags=["agents"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
api_router.include_router(verification_code.router, prefix="/verification-code", tags=["verification-code"]) 