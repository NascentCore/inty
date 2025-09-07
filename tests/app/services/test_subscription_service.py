import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.sql import Select
from datetime import datetime, timezone

from app.schemas.user import User
from app.services.google_play_service import GooglePlayService
from app.services.subscription_service import SubscriptionService
from app.models.agent import Agent
from app.schemas.subscription import SubscriptionStatusResponse
from app.services.superuser_check import SUPERUSER_LIMIT_CHECK_RESULT


class TestSubscriptionService:
    """Test subscription service methods"""

    @pytest.mark.asyncio
    async def test_check_agent_creation_limit_success(self):
        """Test successful agent creation limit check for subscribed user"""
        # Arrange
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.agent_creation_limit = 5

        # Mock the subscription status call
        subscription_service = SubscriptionService(mock_google_play_service)
        subscription_service.get_user_subscription_status = AsyncMock(
            return_value=mock_subscription_status
        )

        # Mock the database query for agent count
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3  # User has created 3 agents
        mock_db.execute.return_value = mock_result

        # Create a mock user object
        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )

        # Act
        is_allowed, agent_count, limit = (
            await subscription_service.check_agent_creation_limit(mock_db, user)
        )

        # Assert
        assert is_allowed is True  # 3 < 5, so allowed
        assert agent_count == 3
        assert limit == 5

        # Verify the subscription status was called
        subscription_service.get_user_subscription_status.assert_called_once_with(
            mock_db, "user-123"
        )

        # Verify the database query was executed
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args[0][0]
        assert isinstance(call_args, Select)
        # Verify it's counting agents for the specific user
        assert "creator_id = :creator_id_1" in str(call_args)

    @pytest.mark.asyncio
    async def test_check_image_gen_limit_success_superuser(self):
        """Test successful image generation limit check for superuser"""
        mock_google_play_service = AsyncMock(spec=GooglePlayService)

        subscription_service = SubscriptionService(mock_google_play_service)
        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=True,
        )

        is_allowed, used_count, limit = (
            await subscription_service.check_image_gen_limit(db=None, user=user)
        )
        assert is_allowed is True
        assert used_count == -1
        assert limit == -1

    @pytest.mark.asyncio
    async def test_check_agent_creation_limit_free_user(self):
        """Test agent creation limit check for free user who has exceeded the limit"""
        # Arrange
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.agent_creation_limit = 4  # Free user limit

        # Mock the subscription status call
        subscription_service = SubscriptionService(mock_google_play_service)
        subscription_service.get_user_subscription_status = AsyncMock(
            return_value=mock_subscription_status
        )

        # Mock the database query for agent count
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5  # User has created 5 agents
        mock_db.execute.return_value = mock_result

        # Create a mock user object
        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )

        # Act
        is_allowed, agent_count, limit = (
            await subscription_service.check_agent_creation_limit(mock_db, user)
        )

        # Assert
        assert is_allowed is False  # 5 >= 4, so not allowed
        assert agent_count == 5
        assert limit == 4

        # Verify the subscription status was called
        subscription_service.get_user_subscription_status.assert_called_once_with(
            mock_db, "user-123"
        )

        # Verify the database query was executed
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args[0][0]
        assert isinstance(call_args, Select)
        # Verify it's counting agents for the specific user
        assert "creator_id = :creator_id_1" in str(call_args)
