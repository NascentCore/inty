# CREATED_BY_AGENT: GPT-5.2

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints import evaluation
from app.models.user import AuthType
from app.schemas import User as UserSchema


def _make_superuser(*, user_id: str = "admin-1") -> UserSchema:
    return UserSchema(
        id=user_id,
        readable_id=f"readable-{user_id}",
        auth_type=AuthType.GOOGLE.value,
        is_active=True,
        is_superuser=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def evaluation_app(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(evaluation.router, prefix="/api/v1")

    async def override_current_active_user():
        return _make_superuser()

    async def override_get_async_db():
        yield None

    app.dependency_overrides[deps.get_current_active_user] = (
        override_current_active_user
    )
    app.dependency_overrides[deps.get_async_db] = override_get_async_db

    calls: list[tuple[str, str]] = []

    class FakeUserAnalyticsService:
        def __init__(self, db):
            self.db = db

        async def find_user_by_email(self, email: str):
            calls.append(("email", email))
            return {
                "id": "user-from-email",
                "email": email,
                "nickname": "nick",
                "auth_type": "GOOGLE",
                "created_at": None,
            }

        async def find_user_by_id(self, user_id: str):
            calls.append(("user_id", user_id))
            return {
                "id": user_id,
                "email": None,
                "nickname": "nick",
                "auth_type": "GUEST",
                "created_at": None,
            }

        async def get_user_daily_messages(self, user_id: str, start_date=None, end_date=None):
            return []

        async def get_user_today_stats(self, user_id: str):
            return {"today_message_count": 0, "today_session_count": 0}

        async def get_user_sessions(self, user_id: str):
            return []

        async def get_session_messages(self, chat_id: str, page: int = 1, size: int = 50):
            return {"messages": [], "total": 0, "page": page, "size": size, "has_more": False}

    monkeypatch.setattr(
        "app.services.user_analytics_service.UserAnalyticsService",
        FakeUserAnalyticsService,
    )

    app.state._calls = calls
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


def test_user_daily_messages_supports_lookup_by_user_id(evaluation_app: FastAPI):
    with TestClient(evaluation_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/user-daily-messages",
            params={"user_id": "user-123"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "user-123"
    assert evaluation_app.state._calls == [("user_id", "user-123")]


def test_user_daily_messages_supports_lookup_by_email(evaluation_app: FastAPI):
    with TestClient(evaluation_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/user-daily-messages",
            params={"email": "a@example.com"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert evaluation_app.state._calls == [("email", "a@example.com")]


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/evaluation/user-analytics/user-daily-messages",
        "/api/v1/evaluation/user-analytics/user-today-stats",
        "/api/v1/evaluation/user-analytics/user-sessions",
    ],
)
def test_user_lookup_requires_exactly_one_identifier(
    evaluation_app: FastAPI, endpoint: str
):
    with TestClient(evaluation_app) as client:
        missing = client.get(endpoint)
        both = client.get(endpoint, params={"email": "a@example.com", "user_id": "u1"})

    assert missing.status_code == 400
    assert both.status_code == 400
