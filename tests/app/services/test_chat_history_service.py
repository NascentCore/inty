import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chat_history_service import (
    _parse_message_content,
    get_latest_ai_message_info,
    get_latest_user_message_id,
)


class TestChatHistoryService:
    """Test chat history service functionality"""

    def test_parse_message_content_system_type(self) -> None:
        raw = json.dumps({"type": "system", "data": {"content": "gate"}})
        assert _parse_message_content(raw) == {"content": "gate", "role": "system"}

    @pytest.mark.asyncio
    async def test_get_latest_ai_message_info_returns_none_when_no_chat_history(self):
        """Test that get_latest_ai_message_info returns None when no chat history is found"""
        # Create a mock database session
        mock_db = AsyncMock()
        
        # Create a mock result that returns None when scalar_one_or_none is called
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        
        # Mock the execute method to return our mock result
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the function with a non-existent session_id
        result = await get_latest_ai_message_info(mock_db, "non-existent-session-id")
        
        # Assert that the function returns None when no chat history is found
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_user_message_id_returns_none_when_no_user_message(self):
        """get_latest_user_message_id 在无用户消息时返回 None"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await get_latest_user_message_id(mock_db, "no-user-msg-session")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_user_message_id_returns_id_when_user_message_exists(self):
        """get_latest_user_message_id 在存在用户消息时返回该消息的 id"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (99,)
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await get_latest_user_message_id(mock_db, "session-with-user-msg")
        assert result == 99
