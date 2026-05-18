from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints import users
from app.models.user import AuthType
from app.schemas.user import User as UserSchema
from app.services import user_service


def _make_user(
    user_id: str = "user-1",
    *,
    is_superuser: bool = False,
) -> UserSchema:
    """Create a minimal user schema instance for dependency overrides."""
    return UserSchema(
        id=user_id,
        readable_id=f"readable-{user_id}",
        auth_type=AuthType.GOOGLE.value,
        is_active=True,
        is_superuser=is_superuser,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def users_app():
    """Provide a FastAPI app mounting only the users router."""
    app = FastAPI()
    app.include_router(users.router, prefix="/api/v1")

    test_user = _make_user()

    async def override_current_active_user():
        return test_user

    async def override_get_async_db():
        yield None

    app.dependency_overrides[deps.get_current_active_user] = (
        override_current_active_user
    )
    app.dependency_overrides[deps.get_async_db] = override_get_async_db
    app.state.test_user = test_user

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


def test_get_current_user_profile_happy_path(
    users_app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    """Ensure GET /api/v1/users/me returns the current user info."""
    async def fake_get_user_connector_count(db, user_id):
        assert db is None
        assert user_id == users_app.state.test_user.id
        return 3

    monkeypatch.setattr(
        user_service, "get_user_connector_count", fake_get_user_connector_count
    )

    with TestClient(users_app) as client:
        response = client.get("/api/v1/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["id"] == users_app.state.test_user.id
    assert data["connector_count"] == 3


def test_register_device_token_happy_path(
    users_app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    """Ensure POST /api/v1/users/device/register stores the provided token."""
    recorded_args: dict[str, tuple[str, str]] = {}

    async def fake_register_device_token(db, token: str, user_id: str):
        recorded_args["call"] = (token, user_id)
        return {"token": token, "user_id": user_id}

    monkeypatch.setattr(
        user_service, "register_device_token", fake_register_device_token
    )

    payload = {"token": "projects/test/fcm-token"}

    with TestClient(users_app) as client:
        response = client.post("/api/v1/users/device/register", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "Device token registered successfully"
    assert recorded_args["call"] == (payload["token"], users_app.state.test_user.id)
