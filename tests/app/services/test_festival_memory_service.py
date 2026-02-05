# CREATED_BY_AGENT
"""节日记忆服务单元测试"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.memory_service import get_festival_memories_for_user_agent


class TestGetFestivalMemoriesForUserAgent:
    """get_festival_memories_for_user_agent 返回格式与空结果"""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_memories(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        out = await get_festival_memories_for_user_agent(
            mock_db, "user-1", "agent-1"
        )
        assert out == []

    @pytest.mark.asyncio
    async def test_returns_list_with_festival_date_name_memory(self):
        mock_db = AsyncMock()
        mock_row = (date(2026, 2, 10), "春节", "用户与角色在春节相关的回忆摘要")
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute = AsyncMock(return_value=mock_result)
        out = await get_festival_memories_for_user_agent(
            mock_db, "user-1", "agent-1"
        )
        assert len(out) == 1
        assert out[0]["festival_date"] == "2026-02-10"
        assert out[0]["festival_name"] == "春节"
        assert out[0]["memory"] == "用户与角色在春节相关的回忆摘要"
