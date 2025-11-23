from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints import users, version
from app.models.user import AuthType
from app.schemas import User as UserSchema
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
def version_app(monkeypatch: pytest.MonkeyPatch):
    """Provide a FastAPI app mounting only the version router."""

    app = FastAPI()
    app.include_router(version.router, prefix="/api/v1")

    async def override_current_active_user():
        return _make_user()

    app.dependency_overrides[deps.get_current_active_user] = (
        override_current_active_user
    )

    class FakeGooglePlayService:
        def __init__(self):
            self.last_call: int | None = None

        def check_version_requirement(self, version_code: int):
            self.last_call = version_code
            return {
                "current_version": str(version_code),
                "latest_version": "200",
                "latest_version_code": 200,
                "update_required": False,
                "force_update": False,
                "force_update_reasons": [],
                "minimum_version": "100",
                "changelog": "Minor fixes",
                "download_url": "https://play.google.com/store/apps/details?id=com.ai.inty",
                "message": "ok",
                "error": None,
            }

    fake_service = FakeGooglePlayService()
    app.state.fake_google_play_service = fake_service
    monkeypatch.setattr(version, "google_play_service", fake_service)

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


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


def test_version_check_returns_google_play_result(version_app: FastAPI):
    """Ensure /api/v1/version/check returns the payload from Google Play service."""

    headers = {
        "appVersionCode": "150",
    }

    with TestClient(version_app) as client:
        response = client.post("/api/v1/version/check", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["current_version"] == "150"
    assert body["data"]["latest_version"] == "200"
    assert version_app.state.fake_google_play_service.last_call == 150


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
