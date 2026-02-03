# CREATED_BY_AGENT
"""用户数据分析预计算报告 API 测试"""

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
