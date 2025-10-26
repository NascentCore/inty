from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chat_history_service import get_latest_ai_message_info


class TestChatHistoryService:
    """Test chat history service functionality"""

    @pytest.mark.asyncio
    async def test_get_latest_ai_message_info_returns_none_when_no_chat_history(self):
        """Test that get_latest_ai_message_info returns None when no chat history is found"""
# 创建模拟数据库会话
        mock_db = AsyncMock()
#创建一个结果模拟，当调用scalar_one_or_none时返回None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
# 执行模拟方法返回我们的模拟结果
        mock_db.execute = AsyncMock(return_value=mock_result)
# 使用不存在的session_id调用该函数
        result = await get_latest_ai_message_info(mock_db, "non-existent-session-id")
# 断言当没有找到聊天记录时函数返回None
        assert result is None
