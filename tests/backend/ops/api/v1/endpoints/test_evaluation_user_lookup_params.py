# CREATED_BY_AGENT: GPT-5.2

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.models.user import AuthType
from app.schemas.user import User as UserSchema
from backend.ops.api.v1 import evaluation


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

    async def override_get_async_replica_db():
        yield None

    app.dependency_overrides[deps.get_current_active_user] = (
        override_current_active_user
    )
    app.dependency_overrides[deps.get_async_db] = override_get_async_db
    app.dependency_overrides[deps.get_async_replica_db] = (
        override_get_async_replica_db
    )

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

        async def get_user_daily_messages(
            self, user_id: str, start_date=None, end_date=None
        ):
            return []

        async def get_daily_messages_for_all_users(self, start_date, end_date):
            calls.append(
                ("all_users", f"{start_date.date()}~{end_date.date()}")
            )
            return []

        async def get_user_today_stats(self, user_id: str):
            return {"today_message_count": 0, "today_session_count": 0}

        async def get_user_sessions(self, user_id: str):
            return [
                {
                    "chat_id": "chat-1",
                    "agent_id": "0049ba23-03b1-48bd-bba4-099ce6c79320",
                    "agent_name": "Amber",
                    "agent_avatar_url": "https://cdn.example.com/amber.webp",
                    "created_at": None,
                    "updated_at": None,
                    "message_count": 3,
                }
            ]

        async def get_session_messages(
            self, chat_id: str, page: int = 1, size: int = 50
        ):
            return {
                "messages": [],
                "total": 0,
                "page": page,
                "size": size,
                "has_more": False,
            }

        async def get_paginated_user_agent_conversations_detail(
            self,
            register_start_date,
            register_end_date,
            activity_start_date=None,
            activity_end_date=None,
            page: int = 1,
            size: int = 10,
        ):
            calls.append(("user_agent_page", f"{page}:{size}"))
            calls.append(
                (
                    "user_agent_activity_range",
                    (
                        activity_start_date.date().isoformat()
                        if activity_start_date
                        else None
                    ),
                )
            )
            calls.append(
                (
                    "user_agent_activity_range_end",
                    (
                        activity_end_date.date().isoformat()
                        if activity_end_date
                        else None
                    ),
                )
            )
            return {
                "items": [
                    {
                        "user_id": "user-1",
                        "auth_type": "GOOGLE",
                        "user_created_at": None,
                        "nickname": "nick-1",
                        "email": "u1@example.com",
                        "agent_id": "agent-1",
                        "agent_name": "Agent 1",
                        "session_count": 1,
                        "message_count": 2,
                        "voice_message_count": 0,
                        "sessions": [
                            {
                                "chat_id": "chat-1",
                                "message_count": 2,
                                "voice_message_count": 0,
                                "messages": [
                                    {
                                        "chat_id": "chat-1",
                                        "message_type": "human",
                                        "content": "hello",
                                        "created_at": None,
                                        "audio_url": None,
                                    },
                                    {
                                        "chat_id": "chat-1",
                                        "message_type": "ai",
                                        "content": "hi",
                                        "created_at": None,
                                        "audio_url": None,
                                    },
                                ],
                            }
                        ],
                    }
                ],
                "total": 1,
                "page": page,
                "size": size,
                "has_more": False,
            }

    monkeypatch.setattr(
        "app.services.user_analytics_service.UserAnalyticsService",
        FakeUserAnalyticsService,
    )

    app.state._calls = calls
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


def test_user_daily_messages_supports_lookup_by_user_id(
    evaluation_app: FastAPI,
):
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


def test_user_daily_messages_supports_date_range_without_identifier(
    evaluation_app: FastAPI,
):
    with TestClient(evaluation_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/user-daily-messages",
            params={"start_date": "2026-03-01", "end_date": "2026-03-08"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "ALL_USERS"
    assert body["auth_type"] == "ALL_USERS"
    assert evaluation_app.state._calls == [
        ("all_users", "2026-03-01~2026-03-09")
    ]


def test_user_daily_messages_requires_date_range_when_identifier_missing(
    evaluation_app: FastAPI,
):
    with TestClient(evaluation_app) as client:
        missing = client.get(
            "/api/v1/evaluation/user-analytics/user-daily-messages"
        )

    assert missing.status_code == 400


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/evaluation/user-analytics/user-today-stats",
        "/api/v1/evaluation/user-analytics/user-sessions",
    ],
)
def test_user_lookup_requires_exactly_one_identifier(
    evaluation_app: FastAPI, endpoint: str
):
    with TestClient(evaluation_app) as client:
        missing = client.get(endpoint)
        both = client.get(
            endpoint, params={"email": "a@example.com", "user_id": "u1"}
        )

    assert missing.status_code == 400
    assert both.status_code == 400


def test_user_sessions_response_includes_agent_avatar_url(
    evaluation_app: FastAPI,
):
    with TestClient(evaluation_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/user-sessions",
            params={"user_id": "user-1"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "sessions": [
            {
                "chat_id": "chat-1",
                "agent_id": "0049ba23-03b1-48bd-bba4-099ce6c79320",
                "agent_name": "Amber",
                "agent_avatar_url": "https://cdn.example.com/amber.webp",
                "created_at": None,
                "updated_at": None,
                "message_count": 3,
            }
        ]
    }


def test_user_agent_conversations_detail_defaults_to_page_size_10(
    evaluation_app: FastAPI,
):
    with TestClient(evaluation_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/conversations-detail/user-agent-paginated",
            params={
                "activity_start_date": "2026-03-01",
                "activity_end_date": "2026-03-08",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["size"] == 10
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == "user-1"
    assert body["items"][0]["agent_id"] == "agent-1"
    assert ("user_agent_page", "1:10") in evaluation_app.state._calls
    assert (
        "user_agent_activity_range",
        "2026-03-01",
    ) in evaluation_app.state._calls
    assert (
        "user_agent_activity_range_end",
        "2026-03-09",
    ) in evaluation_app.state._calls


def test_user_agent_conversations_detail_uses_custom_page_and_size(
    evaluation_app: FastAPI,
):
    with TestClient(evaluation_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/conversations-detail/user-agent-paginated",
            params={"page": 3, "size": 7},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 3
    assert body["size"] == 7
    assert ("user_agent_page", "3:7") in evaluation_app.state._calls
