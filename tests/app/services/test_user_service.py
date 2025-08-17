import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.user import User, AuthType
from app.services.user_service import (
    check_user_can_delete_account,
    create_deletion_audit_log,
)


class TestUserDeletion:
    """Test user deletion functionality"""

    @pytest.mark.asyncio
    async def test_check_user_can_delete_account_success(self):
        """Test user can delete account when conditions are met"""
        user = User(
            id="user_test",
            readable_id="10000001",
            auth_type=AuthType.GOOGLE,
            is_active=True,
        )

        # Mock user query
        mock_user_result = MagicMock()
        mock_user_result.scalars.return_value.first.return_value = user

        # Mock subscription query (no active subscriptions)
        mock_subscription_result = MagicMock()
        mock_subscription_result.scalars.return_value.first.return_value = None

        can_delete, message = await check_user_can_delete_account(
            AsyncSessionLocal(), "user_test"
        )

        assert can_delete is True
        assert message == ""

    @pytest.mark.asyncio
    async def test_check_user_can_delete_account_already_deleted(
        self, async_db_session
    ):
        """Test user cannot delete already deleted account"""
        user = User(
            id="user_test",
            readable_id="10000001",
            auth_type=AuthType.GOOGLE,
            deleted_at=datetime.now(UTC),
        )

        # Mock user query
        mock_user_result = MagicMock()
        mock_user_result.scalars.return_value.first.return_value = user
        async_db_session.execute = AsyncMock(return_value=mock_user_result)

        can_delete, message = await check_user_can_delete_account(
            async_db_session, "user_test"
        )

        assert can_delete is False
        assert "已被删除" in message

    @pytest.mark.asyncio
    async def test_create_deletion_audit_log(self, async_db_session):
        """Test creating deletion audit log"""
        user = User(
            id="user_test",
            readable_id="10000001",
            auth_type=AuthType.GOOGLE,
            system_language="en",
        )

        result = await create_deletion_audit_log(
            AsyncSessionLocal(), user, "Test deletion reason", "processor_123"
        )

        assert result.user_id == "user_test"
        assert result.deletion_reason == "Test deletion reason"
        assert result.processor_id == "processor_123"
        assert result.deletion_type == "user_requested"
        async_db_session.add.assert_called_once()
