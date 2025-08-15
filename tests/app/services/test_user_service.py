import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.user import User, AuthType, Gender, DeviceToken
from app.models.user_deletion_log import UserDeletionLog
from app.models.subscription import UserSubscription, SubscriptionStatus
from app.schemas.user import UserUpdate
from app.services.user_service import (
    generate_next_readable_id,
    generate_next_readable_id_sync,
    create_guest_user,
    update_user,
    register_device_token,
    get_users_device_tokens,
    check_user_can_delete_account,
    create_deletion_audit_log,
    get_all_users,
    get_user_connector_count,
)


class TestGenerateReadableId:
    """Test readable ID generation functions"""

    @pytest.mark.asyncio
    async def test_generate_next_readable_id_new_database(self, async_db_session):
        """Test generating readable ID when database is empty"""
        with patch("app.services.user_service.text") as mock_text:
            mock_text.return_value = "SELECT MAX(CAST(readable_id AS INTEGER)) FROM users WHERE readable_id ~ '^[0-9]+$'"

            # Mock empty result
            mock_result = MagicMock()
            mock_result.scalar.return_value = None
            async_db_session.execute = AsyncMock(return_value=mock_result)

            result = await generate_next_readable_id(async_db_session)

            assert result == "10000000"
            async_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_next_readable_id_existing_data(self, async_db_session):
        """Test generating readable ID when database has existing data"""
        with patch("app.services.user_service.text") as mock_text:
            mock_text.return_value = "SELECT MAX(CAST(readable_id AS INTEGER)) FROM users WHERE readable_id ~ '^[0-9]+$'"

            # Mock existing max ID
            mock_result = MagicMock()
            mock_result.scalar.return_value = 10000005
            async_db_session.execute = AsyncMock(return_value=mock_result)

            result = await generate_next_readable_id(async_db_session)

            assert result == "10000006"
            async_db_session.execute.assert_called_once()

    def test_generate_next_readable_id_sync_new_database(self, db_session):
        """Test sync version with empty database"""
        with patch("app.services.user_service.text") as mock_text:
            mock_text.return_value = "SELECT MAX(CAST(readable_id AS INTEGER)) FROM users WHERE readable_id ~ '^[0-9]+$'"

            # Mock empty result
            mock_result = MagicMock()
            mock_result.scalar.return_value = None
            db_session.execute = MagicMock(return_value=mock_result)

            result = generate_next_readable_id_sync(db_session)

            assert result == "10000000"
            db_session.execute.assert_called_once()


class TestCreateGuestUser:
    """Test guest user creation"""

    @pytest.mark.asyncio
    async def test_create_guest_user_new(self, async_db_session):
        """Test creating a new guest user"""
        with (
            patch("app.services.user_service.uid") as mock_uid,
            patch("app.services.user_service.generate_next_readable_id") as mock_gen_id,
        ):

            mock_uid.return_value = "user_test123"
            mock_gen_id.return_value = "10000001"

            # Mock empty result for existing user check
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = None
            async_db_session.execute = AsyncMock(return_value=mock_result)

            result = await create_guest_user(
                async_db_session,
                device_id="device_123",
                system_language="en",
                age_group="18-25",
            )

            assert result.nickname == "Guest__test123"
            assert result.device_id == "device_123"
            assert result.system_language == "en"
            assert result.age_group == "18-25"
            assert result.auth_type == AuthType.GUEST
            assert result.is_active is True

    @pytest.mark.asyncio
    async def test_create_guest_user_existing(self, async_db_session):
        """Test returning existing guest user"""
        existing_user = User(
            id="user_existing",
            readable_id="10000001",
            auth_type=AuthType.GUEST,
            device_id="device_123",
            nickname="Guest_existing",
        )

        # Mock existing user result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_user
        async_db_session.execute = AsyncMock(return_value=mock_result)

        result = await create_guest_user(async_db_session, device_id="device_123")

        assert result == existing_user


class TestUpdateUser:
    """Test user update functionality"""

    @pytest.mark.asyncio
    async def test_update_user_success(self, async_db_session):
        """Test successful user update"""
        existing_user = User(
            id="user_test",
            readable_id="10000001",
            nickname="Old Name",
            auth_type=AuthType.GOOGLE,
        )

        # Mock user query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_user
        async_db_session.execute = AsyncMock(return_value=mock_result)

        user_update = UserUpdate(nickname="New Name")

        result = await update_user(async_db_session, "user_test", user_update)

        assert result.nickname == "New Name"
        async_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, async_db_session):
        """Test update user that doesn't exist"""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        async_db_session.execute = AsyncMock(return_value=mock_result)

        user_update = UserUpdate(nickname="New Name")

        with pytest.raises(ValueError, match="User does not exist"):
            await update_user(async_db_session, "nonexistent", user_update)


class TestDeviceToken:
    """Test device token functionality"""

    @pytest.mark.asyncio
    async def test_register_device_token_new(self, async_db_session):
        """Test registering new device token"""
        # Mock empty result for existing token check
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        async_db_session.execute = AsyncMock(return_value=mock_result)

        result = await register_device_token(
            async_db_session, token="device_token_123", user_id="user_123"
        )

        assert result.token == "device_token_123"
        assert result.user_id == "user_123"
        async_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_device_token_existing(self, async_db_session):
        """Test updating existing device token"""
        existing_token = DeviceToken(token="device_token_123", user_id="user_old")

        # Mock existing token result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_token
        async_db_session.execute = AsyncMock(return_value=mock_result)

        result = await register_device_token(
            async_db_session, token="device_token_123", user_id="user_new"
        )

        assert result.user_id == "user_new"
        async_db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_users_device_tokens(self, async_db_session):
        """Test getting device tokens for multiple users"""
        # Mock tokens result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["token1", "token2"]
        async_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_users_device_tokens(
            async_db_session, user_ids=["user1", "user2"]
        )

        assert result == ["token1", "token2"]


class TestUserDeletion:
    """Test user deletion functionality"""

    @pytest.mark.asyncio
    async def test_check_user_can_delete_account_success(self, async_db_session):
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

        async_db_session.execute = AsyncMock(
            side_effect=[mock_user_result, mock_subscription_result]
        )

        can_delete, message = await check_user_can_delete_account(
            async_db_session, "user_test"
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

        with patch("app.services.user_service.uid") as mock_uid:
            mock_uid.return_value = "del_log_test123"

            result = await create_deletion_audit_log(
                async_db_session, user, "Test deletion reason", "processor_123"
            )

            assert result.user_id == "user_test"
            assert result.deletion_reason == "Test deletion reason"
            assert result.processor_id == "processor_123"
            assert result.deletion_type == "user_requested"
            async_db_session.add.assert_called_once()


class TestUserManagement:
    """Test user management functions"""

    @pytest.mark.asyncio
    async def test_get_all_users_basic(self, async_db_session):
        """Test getting all users without search"""
        users = [
            User(id="user1", readable_id="10000001", nickname="User 1"),
            User(id="user2", readable_id="10000002", nickname="User 2"),
        ]

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Mock users query
        mock_users_result = MagicMock()
        mock_users_result.scalars.return_value.all.return_value = users

        async_db_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_users_result]
        )

        result = await get_all_users(async_db_session, skip=0, limit=10)

        assert result["total"] == 2
        assert len(result["items"]) == 2
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_get_user_connector_count(self, async_db_session):
        """Test getting user connector count"""
        # Mock count result
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        async_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_user_connector_count(async_db_session, "user_test")

        assert result == 5


# Fixtures for testing
@pytest.fixture
def async_db_session():
    """Mock async database session"""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def db_session():
    """Mock sync database session"""
    session = MagicMock(spec=Session)
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.refresh = MagicMock()
    return session
