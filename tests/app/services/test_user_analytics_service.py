from datetime import datetime, timezone

import pytest
from loguru import logger

from app.services.user_analytics_service import UserAnalyticsService


class QueryAndRollbackFailDb:
    """AsyncSession-shaped fake for the query-fail then rollback-fail path."""

    def __init__(self) -> None:
        self.rollback_calls = 0

    async def execute(self, *args, **kwargs) -> None:
        raise RuntimeError("analytics query failed")

    async def rollback(self) -> None:
        self.rollback_calls += 1
        raise RuntimeError("rollback failed")


@pytest.mark.asyncio
async def test_get_users_hitting_chat_limit_logs_rollback_failure() -> None:
    db = QueryAndRollbackFailDb()
    log_messages: list[str] = []
    sink_id = logger.add(lambda message: log_messages.append(str(message)))

    try:
        result = await UserAnalyticsService(db).get_users_hitting_chat_limit(
            datetime(2026, 2, 1, tzinfo=timezone.utc),
            datetime(2026, 2, 2, tzinfo=timezone.utc),
            guest_limit=1,
            google_limit=1,
        )
    finally:
        logger.remove(sink_id)

    assert result == []
    assert db.rollback_calls == 1
    combined_logs = "\n".join(log_messages)
    assert "查询达到限制的用户失败" in combined_logs
    assert "回滚事务失败" in combined_logs
