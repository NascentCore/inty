import contextlib
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient as FastAPITestClient

from app.api import deps
from app.models.user import AuthType
from app.schemas.user import User
from tests.app.api.test_client import TestClient


API_BASE_URL = os.getenv("INTY_API_BASE_URL", "http://localhost:8000")


def _make_user(
    user_id: str = "user-1",
    auth_type: AuthType = AuthType.GOOGLE,
    is_superuser: bool = False,
) -> User:
    return User(
        id=user_id,
        readable_id=f"readable-{user_id}",
        auth_type=auth_type.value if isinstance(auth_type, AuthType) else auth_type,
        is_active=True,
        is_superuser=is_superuser,
        created_at=datetime.now(timezone.utc),
    )


def _create_mock_db_session():
    """Create a mock database session for endpoint queries."""
    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_agent = SimpleNamespace(id="agent-1", name="Test Agent")
    mock_result.first = MagicMock(return_value=mock_agent)
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_agent)

    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.scalar = AsyncMock(return_value=mock_agent)

    return mock_db


@contextlib.contextmanager
def _client_with_user(app: FastAPI, user: User):
    async def override_current_active_user() -> User:
        return user

    app.dependency_overrides[deps.get_current_active_user] = (
        override_current_active_user
    )

    try:
        with FastAPITestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(deps.get_current_active_user, None)


@pytest.fixture
def integration_client():
    base = API_BASE_URL.rstrip("/")
    try:
        httpx.get(f"{base}/", timeout=2.0)
    except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
        pytest.skip(
            f"HTTP API not reachable at {base} ({exc!r}); "
            "start Postgres + backend (see tests/AGENTS.md) for integration_client tests"
        )
    client = TestClient(API_BASE_URL)
    client.create_user()
    try:
        yield client
    finally:
        client.delete_user()
        client.close()
