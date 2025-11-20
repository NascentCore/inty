from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.chat_history import ChatHistory
from app.services.chat_history_service import (
    get_latest_ai_message_info,
    set_message_feedback,
)


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

    @pytest.mark.asyncio
    async def test_set_message_feedback_updates_metadata(self):
        """set_message_feedback stores feedback info in meta_data"""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        chat_history = ChatHistory()
        chat_history.id = 42
        chat_history.meta_data = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = chat_history
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await set_message_feedback(
            db=mock_db,
            session_id="session-1",
            message_id="42",
            feedback_value="UPVOTE",
            user_id="user-1",
        )

        assert result["success"] is True
        assert result["feedback"] == "UPVOTE"
        assert chat_history.meta_data["feedback"]["type"] == "UPVOTE"
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_message_feedback_clears_feedback(self):
        """set_message_feedback removes feedback when feedback_value is None"""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        chat_history = ChatHistory()
        chat_history.id = 7
        chat_history.meta_data = {"feedback": {"type": "DOWNVOTE"}}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = chat_history
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await set_message_feedback(
            db=mock_db,
            session_id="session-2",
            message_id="7",
            feedback_value=None,
            user_id="user-2",
        )

        assert result["success"] is True
        assert result["feedback"] is None
        assert chat_history.meta_data is None
