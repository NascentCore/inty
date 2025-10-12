from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chat_history_service import get_latest_ai_message_info


class TestChatHistoryService:
    """Test chat history service functionality"""

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
