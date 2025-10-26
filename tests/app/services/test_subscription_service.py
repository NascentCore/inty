from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.external_services.google_play_service import GooglePlayService
from app.models.agent import Agent
from app.schemas.subscription import SubscriptionStatusResponse
from app.schemas.user import User
from app.services.subscription_service import SubscriptionService


class TestSubscriptionService:
    """Test subscription service methods"""

    @pytest.mark.asyncio
    async def test_check_agent_creation_limit_success(self):
        """Test successful agent creation limit check for subscribed user"""
＃ 安排
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.is_subscribed = True
        mock_subscription_status.agent_creation_limit = 5
# 模拟订阅状态调用
        subscription_service = SubscriptionService(mock_google_play_service)
        subscription_service.get_user_subscription_status = AsyncMock(
            return_value=mock_subscription_status
        )
# 数据库模拟查询代理计数
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3  # User has created 3 agents
        mock_db.execute.return_value = mock_result
# 创建模拟用户对象
        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )
＃ 行为
        is_allowed, agent_count, limit = (
            await subscription_service.check_agent_creation_limit(mock_db, user)
        )
#断言
        assert is_allowed is True  # 3 < 12, so allowed
        assert agent_count == 3
        assert limit == 12  # subscribed_user_agent_creation_24h_limit from config
# 验证订阅状态是否被调用
        subscription_service.get_user_subscription_status.assert_called_once_with(
            mock_db, "user-123"
        )
# 验证数据库查询是否已执行
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args[0][0]
        assert isinstance(call_args, Select)
# 验证正在特定为用户统计代理
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
    async def test_check_image_gen_limit_guest_user_denied(self):
        """Test that guest users are denied image generation"""
        mock_google_play_service = AsyncMock(spec=GooglePlayService)

        subscription_service = SubscriptionService(mock_google_play_service)
        user = User(
            id="guest-123",
            readable_id="guest123",
            email=None,
            auth_type="GUEST",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )

        is_allowed, used_count, limit = (
            await subscription_service.check_image_gen_limit(db=None, user=user)
        )
        assert is_allowed is False
        assert used_count == 0
        assert limit == 0

    @pytest.mark.asyncio
    async def test_check_image_gen_limit_free_user_within_limit(self):
        """Test image generation limit check for free user within 24h limit"""
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.is_subscribed = False

        subscription_service = SubscriptionService(mock_google_play_service)
        subscription_service.get_user_subscription_status = AsyncMock(
            return_value=mock_subscription_status
        )
#数据库模拟查询24小时图像生成
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2  # User has generated 2 images in 24h
        mock_db.execute.return_value = mock_result

        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )

        is_allowed, used_count, limit = (
            await subscription_service.check_image_gen_limit(db=mock_db, user=user)
        )
        assert is_allowed is True  # 2 < 4 (free user limit)
        assert used_count == 2
        assert limit == 4  # free_user_image_gen_24h_limit

    @pytest.mark.asyncio
    async def test_check_image_gen_limit_subscribed_user_within_limit(self):
        """Test image generation limit check for subscribed user within 24h limit"""
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.is_subscribed = True

        subscription_service = SubscriptionService(mock_google_play_service)
        subscription_service.get_user_subscription_status = AsyncMock(
            return_value=mock_subscription_status
        )
#数据库模拟查询24小时图像生成
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5  # User has generated 5 images in 24h
        mock_db.execute.return_value = mock_result

        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )

        is_allowed, used_count, limit = (
            await subscription_service.check_image_gen_limit(db=mock_db, user=user)
        )
        assert is_allowed is True  # 5 < 8 (subscribed user limit)
        assert used_count == 5
        assert limit == 8  # subscribed_user_image_gen_24h_limit

    @pytest.mark.asyncio
    async def test_check_agent_creation_limit_free_user_within_limit(self):
        """Test agent creation limit check for free user within 24h limit"""
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.is_subscribed = False

        subscription_service = SubscriptionService(mock_google_play_service)
        subscription_service.get_user_subscription_status = AsyncMock(
            return_value=mock_subscription_status
        )
# 模拟24小时代理创建统计的数据库查询
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3  # User has created 3 agents in 24h
        mock_db.execute.return_value = mock_result

        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )

        is_allowed, agent_count, limit = (
            await subscription_service.check_agent_creation_limit(mock_db, user)
        )
        assert is_allowed is True  # 3 < 6 (free user limit)
        assert agent_count == 3
        assert limit == 6  # free_user_agent_creation_24h_limit

    @pytest.mark.asyncio
    async def test_check_agent_creation_limit_subscribed_user_within_limit(self):
        """Test agent creation limit check for subscribed user within 24h limit"""
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.is_subscribed = True

        subscription_service = SubscriptionService(mock_google_play_service)
        subscription_service.get_user_subscription_status = AsyncMock(
            return_value=mock_subscription_status
        )
# 模拟24小时代理创建统计的数据库查询
        mock_result = MagicMock()
        mock_result.scalar.return_value = 8  # User has created 8 agents in 24h
        mock_db.execute.return_value = mock_result

        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )

        is_allowed, agent_count, limit = (
            await subscription_service.check_agent_creation_limit(mock_db, user)
        )
        assert is_allowed is True  # 8 < 12 (subscribed user limit)
        assert agent_count == 8
        assert limit == 12  # subscribed_user_agent_creation_24h_limit

    @pytest.mark.asyncio
    async def test_check_agent_creation_limit_free_user_over_limit(self):
        """Test agent creation limit check for free user over 24h limit"""
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.is_subscribed = False

        subscription_service = SubscriptionService(mock_google_play_service)
        subscription_service.get_user_subscription_status = AsyncMock(
            return_value=mock_subscription_status
        )
# 模拟24小时代理创建统计的数据库查询
        mock_result = MagicMock()
        mock_result.scalar.return_value = (
            7  # User has created 7 agents in 24h (over limit of 6)
        )
        mock_db.execute.return_value = mock_result

        user = User(
            id="user-123",
            readable_id="user123",
            email="test@example.com",
            auth_type="google",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            is_superuser=False,
        )

        is_allowed, agent_count, limit = (
            await subscription_service.check_agent_creation_limit(mock_db, user)
        )
        assert is_allowed is False  # 7 >= 6 (free user limit)
        assert agent_count == 7
        assert limit == 6  # free_user_agent_creation_24h_limit
