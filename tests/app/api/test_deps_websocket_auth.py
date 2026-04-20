"""
Contract test: WebSocket token auth must not raise when auth snapshot implies re-check.

Regression: get_user_from_token used _get_user_from_auth_snapshot(..., HTTPException);
Starlette HTTPException is not jose.JWTError, so ExpiredSignatureError handling did not
apply and HTTPException could bubble after WebSocket accept (prod ASGI errors).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api import deps
from app.core.security import create_access_token
from app.models.user import AuthType, User
from app.services.cache_service import cache_service


def _mock_db_returning_user(user: User) -> AsyncMock:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=user)
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


def test_get_user_from_token_deleted_snapshot_falls_back_to_db():
    """
    Cache may still hold a pre-deletion snapshot when JWT is valid; WebSocket path must
    fall back to DB instead of raising HTTPException.
    """
    cache_service.clear_all_caches()
    user = User(
        id="user-ws-snapshot-del",
        readable_id="r1",
        nickname="n",
        auth_type=AuthType.GOOGLE,
        google_id="g",
        is_superuser=False,
        deleted_at=None,
    )
    snap = deps._build_user_auth_snapshot(user)
    snap["deleted_at"] = datetime.now(timezone.utc)
    cache_service.set_user_auth_snapshot(user.id, snap, ttl=120)

    token = create_access_token(user.id, expires_delta=timedelta(minutes=5))
    mock_db = _mock_db_returning_user(user)

    out = asyncio.run(deps.get_user_from_token(token, mock_db))
    assert out is not None
    assert out.id == user.id
    cache_service.clear_all_caches()


def test_get_user_from_token_expired_jwt_returns_none():
    cache_service.clear_all_caches()
    user = User(
        id="user-ws-expired",
        readable_id="r2",
        nickname="n",
        auth_type=AuthType.GOOGLE,
        google_id="g",
        is_superuser=False,
        deleted_at=None,
    )
    token = create_access_token(user.id, expires_delta=timedelta(seconds=-1))
    mock_db = _mock_db_returning_user(user)

    out = asyncio.run(deps.get_user_from_token(token, mock_db))
    assert out is None
    mock_db.execute.assert_not_called()
    cache_service.clear_all_caches()
