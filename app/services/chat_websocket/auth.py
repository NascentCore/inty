"""Authentication helpers for chat WebSocket sessions."""

from __future__ import annotations

from typing import Optional

from fastapi import WebSocket
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.user import User as UserSchema

async def _get_current_user_from_websocket(
    websocket: WebSocket, db: AsyncSession
) -> Optional[User]:
    auth = websocket.headers.get("authorization")
    token = None
    if auth:
        parts = auth.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
    if token is None or token == "":
        token = websocket.query_params.get("token")
    if token is None or token == "":
        return None
    return await deps.get_user_from_token(token, db)

async def _resolve_assumed_chat_websocket_user(
    *,
    operator: User,
    assume_user_id: Optional[str],
    db: AsyncSession,
) -> UserSchema:
    """
    Evaluation: superuser may pass assume_user_id query (same semantics as live_chat WS).
    Matches HTTP X-Assume-User-Id for chat so eval WebSocket hits the same code path as production /ws.
    """
    operator_schema = UserSchema.model_validate(operator, from_attributes=True)
    if not assume_user_id or not str(assume_user_id).strip():
        return operator_schema
    if not operator.is_superuser:
        logger.warning(
            "chat WebSocket assume_user_id ignored: operator is not superuser "
            f"operator_id={operator.id}"
        )
        return operator_schema
    user_id = str(assume_user_id).strip()
    row = await db.execute(select(User).where(User.id == user_id))
    assumed = row.scalar_one_or_none()
    if assumed is not None and not assumed.deleted_at:
        logger.info(
            "chat WebSocket assuming user: operator={} assumed={}",
            operator.id,
            assumed.id,
        )
        return UserSchema.model_validate(assumed, from_attributes=True)
    logger.warning(
        "chat WebSocket assume_user_id not found or deleted: {}", assume_user_id
    )
    return operator_schema
