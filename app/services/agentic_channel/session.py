"""Agent-channel MemoryStore session bootstrap for provisioning and WS queue serving."""

from __future__ import annotations

from sqlalchemy import select

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.agentic_companion.turn import (
    manager_and_session_for_scope,
)
from app.core.companion_harness.companion.manager import CompanionSession
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.global_services import subscription_service


async def ensure_memory_store_session(scope: AgentScope) -> CompanionSession:
    """Create companion session with synthetic chat id (seeds MemoryStore if needed)."""
    async with AsyncSessionLocal() as db:
        user_row = await db.execute(
            select(User).where(User.id == scope.user_id)
        )
        user = user_row.scalar_one_or_none()
        if user is None:
            raise ValueError(f"user not found: {scope.user_id}")
        subscription = await subscription_service.get_user_current_subscription(
            db, scope.user_id
        )
        model = select_chat_model(
            user=user,
            is_subscribed=bool(subscription),
        )
    _, session = manager_and_session_for_scope(scope, resolved_chat_model=model)
    return session
