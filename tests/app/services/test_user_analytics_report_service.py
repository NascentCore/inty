# CREATED_BY_AGENT
"""用户数据分析预计算报告服务测试"""

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_analytics_report_service import (
    REPLICA_READ_MAX_ATTEMPTS,
    _first_monday_of_year,
    _mondays_in_first_half,
    compute_and_save_daily_report,
    compute_and_save_weekly_report,
    get_missing_daily_report_dates,
    get_missing_weekly_report_dates_first_half,
    get_missing_weekly_report_dates_past_weeks,
)


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def sample_stats():
    return {
        "total_new_users": 100,
        "total_chat_initiators": 10,
        "total_user_messages": 50,
        "total_ai_messages": 90,
        "total_active_sessions": 20,
        "total_voice_requests": 5,
        "avg_messages_per_user": 5.0,
        "avg_sessions_per_user": 2.0,
        "avg_voice_requests_per_user": 0.5,
        "avg_rounds_per_session": 2.5,
        "new_user_open_rate": 10.0,
        "total_image_generation_requests": 3,
        "total_image_generation_success": 2,
        "total_image_generation_failures": 1,
        "image_generation_success_rate": 66.67,
        "total_image_new_generation": 1,
        "total_image_fallback_used": 1,
        "total_live_chat_users": 0,
        "total_live_chat_sessions": 0,
        "total_live_chat_duration": 0,
        "avg_live_chat_sessions_per_user": 0.0,
        "avg_live_chat_duration_per_user": 0.0,
        "avg_live_chat_duration_per_session": 0.0,
    }


@pytest.fixture
def sample_popular_agents():
    return [
        {
            "agent_name": "Agent A",
            "user_count": 10,
            "total_rounds": 80,
            "avg_rounds_per_user": 8.0,
            "pct_sessions_ge_5": 60.0,
            "pct_sessions_ge_10": 30.0,
            "total_sessions": 20,
            "active_sessions": 12,
            "open_rate": 60.0,
        },
        {
            "agent_name": "Agent B",
            "user_count": 7,
            "total_rounds": 120,
            "avg_rounds_per_user": 17.14,
            "pct_sessions_ge_5": 75.0,
            "pct_sessions_ge_10": 50.0,
            "total_sessions": 15,
            "active_sessions": 10,
            "open_rate": 66.67,
        },
        {
            "agent_name": "Agent C",
            "user_count": 4,
            "total_rounds": 60,
            "avg_rounds_per_user": 15.0,
            "pct_sessions_ge_5": 70.0,
            "pct_sessions_ge_10": 40.0,
            "total_sessions": 9,
            "active_sessions": 7,
            "open_rate": 77.78,
        },
    ]


@pytest.mark.asyncio
async def test_compute_and_save_daily_report_skips_existing(mock_db, sample_stats):
    """已存在的日报应跳过"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.user_analytics_report_service.AsyncSessionLocalReplica",
            None,
        ),
        patch(
            "app.services.user_analytics_report_service.UserAnalyticsService"
        ) as MockService,
    ):
        mock_service_instance = AsyncMock()
        mock_service_instance.get_analytics_stats = AsyncMock(return_value=sample_stats)
        mock_service_instance.get_active_session_ids_on_date = AsyncMock(
            return_value=set()
        )
        mock_service_instance.get_new_users = AsyncMock(return_value=[])
        mock_service_instance.get_conversation_rounds = AsyncMock(return_value=[])
        mock_service_instance.get_user_rounds_distribution = AsyncMock(return_value=[])
        mock_service_instance.get_users_hitting_chat_limit = AsyncMock(return_value=[])
        mock_service_instance.get_popular_agents = AsyncMock(return_value=[])
        mock_service_instance.get_generated_images_on_date = AsyncMock(return_value=[])
        MockService.return_value = mock_service_instance

        result = await compute_and_save_daily_report(mock_db, date(2026, 2, 1))

    assert result is None
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()
    mock_service_instance.get_generated_images_on_date.assert_awaited_once_with(
        datetime(2026, 2, 1, tzinfo=timezone.utc),
        datetime(2026, 2, 2, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_compute_and_save_daily_report_creates_new(
    mock_db, sample_stats, sample_popular_agents
):
    """新日报应创建并保存"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.user_analytics_report_service.AsyncSessionLocalReplica",
            None,
        ),
        patch(
            "app.services.user_analytics_report_service.UserAnalyticsService"
        ) as MockService,
    ):
        mock_service_instance = AsyncMock()
        mock_service_instance.get_analytics_stats = AsyncMock(return_value=sample_stats)
        mock_service_instance.get_active_session_ids_on_date = AsyncMock(
            return_value=set()
        )
        mock_service_instance.get_new_users = AsyncMock(return_value=[])
        mock_service_instance.get_conversation_rounds = AsyncMock(return_value=[])
        mock_service_instance.get_user_rounds_distribution = AsyncMock(return_value=[])
        mock_service_instance.get_users_hitting_chat_limit = AsyncMock(return_value=[])
        mock_service_instance.get_popular_agents = AsyncMock(
            return_value=sample_popular_agents
        )
        generated_images = [
            {
                "id": 1001,
                "session_id": "session-1",
                "image_url": "https://storage.googleapis.com/bucket/path.png",
                "meta_data": {"generated_image": {"prompt": "sunset"}},
                "created_at": "2026-02-01T03:00:00+00:00",
            }
        ]
        mock_service_instance.get_generated_images_on_date = AsyncMock(
            return_value=generated_images
        )
        MockService.return_value = mock_service_instance

        result = await compute_and_save_daily_report(mock_db, date(2026, 2, 1))

    assert result is not None
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert result.charts["generated_images"] == generated_images
    assert result.charts["popular_agents"] == sample_popular_agents
    assert result.charts["daily_top_agents_by_rounds"][0]["agent_name"] == "Agent B"
    assert result.charts["daily_top_agents_by_rounds"][0]["total_rounds"] == 120
    assert result.charts["daily_most_discussed_agent"]["agent_name"] == "Agent B"
    mock_service_instance.get_generated_images_on_date.assert_awaited_once_with(
        datetime(2026, 2, 1, tzinfo=timezone.utc),
        datetime(2026, 2, 2, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_compute_and_save_daily_report_fallbacks_to_primary_when_replica_conflicts(
    mock_db, sample_stats, sample_popular_agents
):
    """副本持续 conflict with recovery 时，应回退主库读取并成功保存日报。"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    replica_error = OperationalError(
        statement="SELECT 1",
        params={},
        orig=Exception("canceling statement due to conflict with recovery"),
    )

    with (
        patch(
            "app.services.user_analytics_report_service.AsyncSessionLocalReplica",
            object(),
        ),
        patch(
            "app.services.user_analytics_report_service._read_daily_report_from_replica",
            new=AsyncMock(side_effect=[replica_error] * REPLICA_READ_MAX_ATTEMPTS),
        ) as mock_replica_reader,
        patch(
            "app.services.user_analytics_report_service.UserAnalyticsService"
        ) as MockService,
    ):
        mock_service_instance = AsyncMock()
        mock_service_instance.get_analytics_stats = AsyncMock(return_value=sample_stats)
        mock_service_instance.get_active_session_ids_on_date = AsyncMock(
            return_value=set()
        )
        mock_service_instance.get_new_users = AsyncMock(return_value=[])
        mock_service_instance.get_conversation_rounds = AsyncMock(return_value=[])
        mock_service_instance.get_user_rounds_distribution = AsyncMock(return_value=[])
        mock_service_instance.get_users_hitting_chat_limit = AsyncMock(return_value=[])
        mock_service_instance.get_popular_agents = AsyncMock(
            return_value=sample_popular_agents
        )
        mock_service_instance.get_generated_images_on_date = AsyncMock(return_value=[])
        MockService.return_value = mock_service_instance

        result = await compute_and_save_daily_report(mock_db, date(2026, 2, 1))

    assert result is not None
    assert mock_replica_reader.await_count == REPLICA_READ_MAX_ATTEMPTS
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_service_instance.get_generated_images_on_date.assert_awaited_once_with(
        datetime(2026, 2, 1, tzinfo=timezone.utc),
        datetime(2026, 2, 2, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_compute_and_save_weekly_report_skips_existing(mock_db, sample_stats):
    """已存在的周报应跳过"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.user_analytics_report_service.AsyncSessionLocalReplica",
            None,
        ),
        patch(
            "app.services.user_analytics_report_service.UserAnalyticsService"
        ) as MockService,
    ):
        mock_service_instance = AsyncMock()
        mock_service_instance.get_analytics_stats = AsyncMock(return_value=sample_stats)
        MockService.return_value = mock_service_instance

        result = await compute_and_save_weekly_report(mock_db, date(2026, 1, 27))

    assert result is None
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_compute_and_save_weekly_report_creates_new(mock_db, sample_stats):
    """新周报应创建并保存"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.user_analytics_report_service.AsyncSessionLocalReplica",
            None,
        ),
        patch(
            "app.services.user_analytics_report_service.UserAnalyticsService"
        ) as MockService,
    ):
        mock_service_instance = AsyncMock()
        mock_service_instance.get_analytics_stats = AsyncMock(return_value=sample_stats)
        MockService.return_value = mock_service_instance

        result = await compute_and_save_weekly_report(mock_db, date(2026, 1, 27))

    assert result is not None
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_compute_and_save_weekly_report_fallbacks_to_primary_when_replica_conflicts(
    mock_db, sample_stats
):
    """周报副本持续 conflict with recovery 时，应回退主库读取并成功保存周报。"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    replica_error = OperationalError(
        statement="SELECT 1",
        params={},
        orig=Exception("canceling statement due to conflict with recovery"),
    )

    @asynccontextmanager
    async def fake_replica_session():
        replica_db = AsyncMock(spec=AsyncSession)
        yield replica_db

    service_get_stats_side_effects = [replica_error] * REPLICA_READ_MAX_ATTEMPTS + [
        sample_stats
    ]

    with (
        patch(
            "app.services.user_analytics_report_service.AsyncSessionLocalReplica",
            lambda: fake_replica_session(),
        ),
        patch(
            "app.services.user_analytics_report_service.UserAnalyticsService"
        ) as MockService,
        patch(
            "app.services.user_analytics_report_service.asyncio.sleep",
            new=AsyncMock(),
        ) as mock_sleep,
    ):
        mock_service_instance = AsyncMock()
        mock_service_instance.get_analytics_stats = AsyncMock(
            side_effect=service_get_stats_side_effects
        )
        mock_service_instance.get_new_users = AsyncMock(return_value=[])
        mock_service_instance.get_conversation_rounds = AsyncMock(return_value=[])
        mock_service_instance.get_user_rounds_distribution = AsyncMock(return_value=[])
        mock_service_instance.get_users_hitting_chat_limit = AsyncMock(return_value=[])
        mock_service_instance.get_popular_agents = AsyncMock(return_value=[])
        MockService.return_value = mock_service_instance

        result = await compute_and_save_weekly_report(mock_db, date(2026, 1, 27))

    assert result is not None
    assert (
        mock_service_instance.get_analytics_stats.await_count
        == REPLICA_READ_MAX_ATTEMPTS + 1
    )
    assert mock_sleep.await_count == REPLICA_READ_MAX_ATTEMPTS - 1
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_first_monday_of_year():
    assert _first_monday_of_year(2026) == date(2026, 1, 5)
    assert _first_monday_of_year(2025) == date(2025, 1, 6)


def test_mondays_in_first_half():
    mondays = _mondays_in_first_half(2026)
    assert mondays[0] == date(2026, 1, 5)
    assert mondays[-1].month == 6
    assert all(d.weekday() == 0 for d in mondays)


@pytest.mark.asyncio
async def test_get_missing_daily_report_dates_all_missing(mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.user_analytics_report_service.datetime") as mock_dt:
        mock_dt.now.return_value = MagicMock()
        mock_dt.now.return_value.date.return_value = date(2026, 2, 2)
        missing = await get_missing_daily_report_dates(mock_db, days=3)

    assert len(missing) == 3
    assert set(missing) == {date(2026, 1, 30), date(2026, 1, 31), date(2026, 2, 1)}


@pytest.mark.asyncio
async def test_get_missing_daily_report_dates_partial_existing(mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [date(2026, 2, 1)]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.user_analytics_report_service.datetime") as mock_dt:
        mock_dt.now.return_value = MagicMock()
        mock_dt.now.return_value.date.return_value = date(2026, 2, 2)
        missing = await get_missing_daily_report_dates(mock_db, days=3)

    assert len(missing) == 2
    assert set(missing) == {date(2026, 1, 30), date(2026, 1, 31)}


@pytest.mark.asyncio
async def test_get_missing_weekly_report_dates_first_half_all_missing(
    mock_db,
):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    missing = await get_missing_weekly_report_dates_first_half(mock_db, 2026)
    assert len(missing) > 0
    assert all(d.weekday() == 0 for d in missing)
    assert all(d.month <= 6 for d in missing)


@pytest.mark.asyncio
async def test_get_missing_weekly_report_dates_first_half_partial_existing(
    mock_db,
):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [date(2026, 1, 5)]
    mock_db.execute = AsyncMock(return_value=mock_result)

    missing = await get_missing_weekly_report_dates_first_half(mock_db, 2026)
    assert date(2026, 1, 5) not in missing


@pytest.mark.asyncio
async def test_get_missing_weekly_report_dates_past_weeks(mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.user_analytics_report_service.datetime") as mock_dt:
        mock_dt.now.return_value = MagicMock()
        mock_dt.now.return_value.date.return_value = date(2026, 2, 2)
        missing = await get_missing_weekly_report_dates_past_weeks(mock_db, weeks=7)

    assert len(missing) == 7
    assert all(d.weekday() == 0 for d in missing)
    base_expected = date(2026, 1, 26)
    assert set(missing) == {base_expected - timedelta(days=i * 7) for i in range(7)}
