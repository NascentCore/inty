# CREATED_BY_AGENT
"""用户数据分析预计算报告 API 测试"""

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


def _build_stats() -> dict:
    return {
        "total_new_users": 1,
        "total_chat_initiators": 1,
        "total_user_messages": 1,
        "total_ai_messages": 1,
        "total_active_sessions": 1,
        "total_voice_requests": 0,
        "avg_messages_per_user": 1.0,
        "avg_sessions_per_user": 1.0,
        "avg_voice_requests_per_user": 0.0,
        "avg_rounds_per_session": 1.0,
        "new_user_open_rate": 100.0,
        "total_image_generation_requests": 0,
        "total_image_generation_success": 0,
        "total_image_generation_failures": 0,
        "image_generation_success_rate": 0.0,
        "total_image_new_generation": 0,
        "total_image_fallback_used": 0,
        "total_live_chat_users": 0,
        "total_live_chat_sessions": 0,
        "total_live_chat_duration": 0,
        "avg_live_chat_sessions_per_user": 0.0,
        "avg_live_chat_duration_per_user": 0.0,
        "avg_live_chat_duration_per_session": 0.0,
    }


def _build_popular_agents_for_fallback() -> list[dict]:
    return [
        {
            "agent_name": "Role Alpha",
            "user_count": 3,
            "total_rounds": 28,
            "avg_rounds_per_user": 9.33,
            "pct_sessions_ge_5": 50.0,
            "pct_sessions_ge_10": 33.33,
            "total_sessions": 8,
            "active_sessions": 4,
            "open_rate": 50.0,
        },
        {
            "agent_name": "Role Beta",
            "user_count": 2,
            "total_rounds": 35,
            "avg_rounds_per_user": 17.5,
            "pct_sessions_ge_5": 60.0,
            "pct_sessions_ge_10": 40.0,
            "total_sessions": 5,
            "active_sessions": 3,
            "open_rate": 60.0,
        },
    ]


@pytest.fixture
def reports_app():
    """提供挂载 evaluation 路由的 FastAPI 应用，用于测试 reports 端点"""
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

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


def test_user_analytics_reports_returns_empty_when_no_data(
    reports_app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    """无预计算数据时返回空列表"""
    from unittest.mock import AsyncMock, MagicMock

    async def mock_execute(stmt):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)

    async def override_get_async_replica_db():
        yield mock_db

    reports_app.dependency_overrides[deps.get_async_replica_db] = (
        override_get_async_replica_db
    )

    with TestClient(reports_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/reports",
            params={"report_type": "daily"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "reports" in body
    assert body["reports"] == []


def test_user_analytics_reports_can_skip_charts(
    reports_app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    """显式关闭图表数据时返回空 charts"""
    from unittest.mock import AsyncMock, MagicMock

    row = MagicMock()
    row.id = "report-1"
    row.report_type = "daily"
    row.report_date = datetime(2026, 2, 5, tzinfo=timezone.utc).date()
    row.stats = _build_stats()
    row.charts = {"new_users": [{"date": "2026-02-05", "count": 1}]}
    row.created_at = None

    async def mock_execute(stmt):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [row]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)

    async def override_get_async_replica_db():
        yield mock_db

    reports_app.dependency_overrides[deps.get_async_replica_db] = (
        override_get_async_replica_db
    )

    with TestClient(reports_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/reports",
            params={"report_type": "daily", "include_charts": "false"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["reports"][0]["charts"] is None
    assert body["reports"][0]["daily_top_agents_by_rounds"] == []
    assert body["reports"][0]["daily_most_discussed_agent"] is None


def test_user_analytics_reports_fallback_daily_top_agents_when_charts_skipped(
    reports_app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    """旧日报缺少 daily_top 字段时，应基于 popular_agents 兜底计算"""
    from unittest.mock import AsyncMock, MagicMock

    row = MagicMock()
    row.id = "report-2"
    row.report_type = "daily"
    row.report_date = datetime(2026, 2, 6, tzinfo=timezone.utc).date()
    row.stats = _build_stats()
    row.charts = {"popular_agents": _build_popular_agents_for_fallback()}
    row.created_at = None

    async def mock_execute(stmt):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [row]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)

    async def override_get_async_replica_db():
        yield mock_db

    reports_app.dependency_overrides[deps.get_async_replica_db] = (
        override_get_async_replica_db
    )

    with TestClient(reports_app) as client:
        resp = client.get(
            "/api/v1/evaluation/user-analytics/reports",
            params={"report_type": "daily", "include_charts": "false"},
        )

    assert resp.status_code == 200
    body = resp.json()
    report = body["reports"][0]
    assert report["charts"] is None
    assert report["daily_top_agents_by_rounds"][0]["agent_name"] == "Role Beta"
    assert report["daily_top_agents_by_rounds"][0]["total_rounds"] == 35
    assert report["daily_most_discussed_agent"]["agent_name"] == "Role Beta"
