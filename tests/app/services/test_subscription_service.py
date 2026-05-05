import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.external_services.google_play_service import GooglePlayService
from app.models.agent import Agent
from app.schemas.subscription import SubscriptionStatusResponse
from app.schemas.user import User
from app.services.subscription_service import (
    SubscriptionService,
    is_google_play_rtdn_notification,
)


class TestSubscriptionService:
    """Test subscription service methods"""

    @pytest.mark.asyncio
    async def test_check_agent_creation_limit_success(self):
        """Test successful agent creation limit check for subscribed user"""
        # Arrange
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_subscription_status = MagicMock(spec=SubscriptionStatusResponse)
        mock_subscription_status.is_subscribed = True
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
        random_user_id = str(uuid.uuid4())
        user = User(
            id=random_user_id,
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
        assert is_allowed is True  # 3 < 12, so allowed
        assert agent_count == 3
        assert limit == 12  # subscribed_user_agent_creation_24h_limit from config

        # Verify the subscription status was called
        subscription_service.get_user_subscription_status.assert_called_once_with(
            mock_db, random_user_id
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
        random_user_id = str(uuid.uuid4())
        user = User(
            id=random_user_id,
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
        random_user_id = str(uuid.uuid4())
        user = User(
            id=random_user_id,
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

        # Mock the database query for 24h image generation count
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2  # User has generated 2 images in 24h
        mock_db.execute.return_value = mock_result

        random_user_id = str(uuid.uuid4())
        user = User(
            id=random_user_id,
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

        # Mock the database query for 24h image generation count
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5  # User has generated 5 images in 24h
        mock_db.execute.return_value = mock_result
        random_user_id = str(uuid.uuid4())
        user = User(
            id=random_user_id,
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

        # Mock the database query for 24h agent creation count
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3  # User has created 3 agents in 24h
        mock_db.execute.return_value = mock_result

        random_user_id = str(uuid.uuid4())
        user = User(
            id=random_user_id,
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

        # Mock the database query for 24h agent creation count
        mock_result = MagicMock()
        mock_result.scalar.return_value = 8  # User has created 8 agents in 24h
        mock_db.execute.return_value = mock_result

        random_user_id = str(uuid.uuid4())
        user = User(
            id=random_user_id,
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

        # Mock the database query for 24h agent creation count
        mock_result = MagicMock()
        mock_result.scalar.return_value = (
            7  # User has created 7 agents in 24h (over limit of 6)
        )
        mock_db.execute.return_value = mock_result

        random_user_id = str(uuid.uuid4())
        user = User(
            id=random_user_id,
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

    @pytest.mark.asyncio
    async def test_record_usage_retries_with_isolated_session_when_caller_session_fails(
        self,
        monkeypatch,
    ):
        mock_google_play_service = AsyncMock(spec=GooglePlayService)
        subscription_service = SubscriptionService(mock_google_play_service)

        broken_db = AsyncMock(spec=AsyncSession)
        isolated_db = AsyncMock(spec=AsyncSession)
        usage_record = SimpleNamespace(id="usage-record-1")

        async def fake_record_usage_impl(db, user_id, usage_type, usage_count, extra_data):
            if db is broken_db:
                return None
            if db is isolated_db:
                return usage_record
            return None

        subscription_service._record_usage_impl = AsyncMock(
            side_effect=fake_record_usage_impl
        )

        async def fake_get_async_db():
            yield isolated_db

        monkeypatch.setattr("app.api.deps.get_async_db", fake_get_async_db)

        result = await subscription_service.record_usage(
            db=broken_db,
            user_id="user-1",
            usage_type="live_chat",
            usage_count=1,
            extra_data={"source": "test"},
        )

        assert result is usage_record
        assert subscription_service._record_usage_impl.await_count == 2
        assert (
            subscription_service._record_usage_impl.await_args_list[0].args[0]
            is broken_db
        )
        assert (
            subscription_service._record_usage_impl.await_args_list[1].args[0]
            is isolated_db
        )


class TestRTDNSubscriptionNotification:
    """测试 RTDN 订阅通知处理路径，确保不触发懒加载错误"""

    @pytest.mark.asyncio
    async def test_update_subscription_by_notification_type_with_plan_preloaded(self):
        """测试 _update_subscription_by_notification_type 当 plan 已预加载时正常工作"""
        mock_google_play_service = MagicMock(spec=GooglePlayService)
        mock_google_play_service.get_subscription_details.return_value = {
            "expiry_time": datetime.now(timezone.utc),
            "auto_renewing": True,
        }

        mock_db = AsyncMock(spec=AsyncSession)

        # 创建带有预加载 plan 的 subscription mock
        mock_plan = MagicMock()
        mock_plan.id = str(uuid.uuid4())
        mock_plan.google_play_product_id = "com.ai.inty.premium.monthly"
        mock_plan.price = 9.99
        mock_plan.currency = "USD"

        mock_subscription = MagicMock()
        mock_subscription.id = str(uuid.uuid4())
        mock_subscription.user_id = str(uuid.uuid4())
        mock_subscription.plan_id = mock_plan.id
        mock_subscription.plan = mock_plan  # plan 已预加载
        mock_subscription.google_play_purchase_token = "test_token_123"
        mock_subscription.extra_data = {}

        subscription_service = SubscriptionService(mock_google_play_service)

        # 测试续费通知（notificationType=2）
        notification_data = {"subscriptionNotification": {"notificationType": 2}}

        await subscription_service._update_subscription_by_notification_type(
            mock_db, mock_subscription, 2, notification_data
        )

        # 验证 Google Play API 被正确调用
        mock_google_play_service.get_subscription_details.assert_called_once_with(
            "com.ai.inty.premium.monthly", "test_token_123"
        )
        # 验证 db.commit 被调用
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_subscription_by_notification_type_without_plan_defensive(
        self,
    ):
        """测试 _update_subscription_by_notification_type 当 plan=None 时防御式查询"""
        mock_google_play_service = MagicMock(spec=GooglePlayService)
        mock_google_play_service.get_subscription_details.return_value = {
            "expiry_time": datetime.now(timezone.utc),
            "auto_renewing": True,
        }

        mock_db = AsyncMock(spec=AsyncSession)

        # 创建 plan mock
        mock_plan = MagicMock()
        mock_plan.id = str(uuid.uuid4())
        mock_plan.google_play_product_id = "com.ai.inty.premium.monthly"
        mock_plan.price = 9.99
        mock_plan.currency = "USD"

        # Mock db.execute 返回 plan
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_plan
        mock_db.execute.return_value = mock_result

        # 创建没有预加载 plan 的 subscription mock
        mock_subscription = MagicMock()
        mock_subscription.id = str(uuid.uuid4())
        mock_subscription.user_id = str(uuid.uuid4())
        mock_subscription.plan_id = mock_plan.id
        mock_subscription.plan = None  # plan 未预加载
        mock_subscription.google_play_purchase_token = "test_token_456"
        mock_subscription.extra_data = {}

        subscription_service = SubscriptionService(mock_google_play_service)

        # 测试取消通知（notificationType=3）
        notification_data = {"subscriptionNotification": {"notificationType": 3}}

        await subscription_service._update_subscription_by_notification_type(
            mock_db, mock_subscription, 3, notification_data
        )

        # 验证防御式查询被执行
        mock_db.execute.assert_called()
        # 验证 Google Play API 被正确调用（使用查询到的 plan）
        mock_google_play_service.get_subscription_details.assert_called_once_with(
            "com.ai.inty.premium.monthly", "test_token_456"
        )
        # 验证 db.commit 被调用
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_renewal_transaction_with_plan_preloaded(self):
        """测试 _create_renewal_transaction 当 plan 已预加载时正常工作"""
        mock_google_play_service = MagicMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)

        # 创建带有预加载 plan 的 subscription mock
        mock_plan = MagicMock()
        mock_plan.id = str(uuid.uuid4())
        mock_plan.price = 9.99
        mock_plan.currency = "USD"

        mock_subscription = MagicMock()
        mock_subscription.id = str(uuid.uuid4())
        mock_subscription.user_id = str(uuid.uuid4())
        mock_subscription.plan_id = mock_plan.id
        mock_subscription.plan = mock_plan  # plan 已预加载
        mock_subscription.google_play_purchase_token = "test_token_renewal"

        subscription_service = SubscriptionService(mock_google_play_service)

        notification_data = {"subscriptionNotification": {"notificationType": 2}}

        await subscription_service._create_renewal_transaction(
            mock_db, mock_subscription, notification_data
        )

        # 验证 db.add 被调用（添加交易记录）
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_renewal_transaction_without_plan_defensive(self):
        """测试 _create_renewal_transaction 当 plan=None 时防御式查询"""
        mock_google_play_service = MagicMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)

        # 创建 plan mock
        mock_plan = MagicMock()
        mock_plan.id = str(uuid.uuid4())
        mock_plan.price = 9.99
        mock_plan.currency = "USD"

        # Mock db.execute 返回 plan
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_plan
        mock_db.execute.return_value = mock_result

        # 创建没有预加载 plan 的 subscription mock
        mock_subscription = MagicMock()
        mock_subscription.id = str(uuid.uuid4())
        mock_subscription.user_id = str(uuid.uuid4())
        mock_subscription.plan_id = mock_plan.id
        mock_subscription.plan = None  # plan 未预加载
        mock_subscription.google_play_purchase_token = "test_token_renewal_defensive"

        subscription_service = SubscriptionService(mock_google_play_service)

        notification_data = {"subscriptionNotification": {"notificationType": 2}}

        await subscription_service._create_renewal_transaction(
            mock_db, mock_subscription, notification_data
        )

        # 验证防御式查询被执行
        mock_db.execute.assert_called_once()
        # 验证 db.add 被调用（添加交易记录）
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_refund_without_plan_defensive(self):
        """测试 handle_refund 当 plan=None 时防御式查询"""
        mock_google_play_service = MagicMock(spec=GooglePlayService)
        mock_db = AsyncMock(spec=AsyncSession)

        # 创建 plan mock
        mock_plan = MagicMock()
        mock_plan.id = str(uuid.uuid4())
        mock_plan.price = 9.99
        mock_plan.currency = "USD"

        # Mock db.execute 返回 plan
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_plan
        mock_db.execute.return_value = mock_result

        # 创建没有预加载 plan 的 subscription mock
        mock_subscription = MagicMock()
        mock_subscription.id = str(uuid.uuid4())
        mock_subscription.user_id = str(uuid.uuid4())
        mock_subscription.plan_id = mock_plan.id
        mock_subscription.plan = None  # plan 未预加载
        mock_subscription.google_play_purchase_token = "test_token_refund"
        mock_subscription.google_play_order_id = "order_123"
        mock_subscription.extra_data = {}

        subscription_service = SubscriptionService(mock_google_play_service)

        refund_data = {"amount": 5.00}

        await subscription_service.handle_refund(
            mock_db, mock_subscription, refund_data
        )

        # 验证防御式查询被执行
        mock_db.execute.assert_called_once()
        # 验证 db.add 被调用（添加退款交易记录）
        mock_db.add.assert_called_once()
        # 验证 db.commit 被调用
        mock_db.commit.assert_called_once()


class TestGooglePlayRtdnDetection:
    """Regression: Pub/Sub may deliver non-RTDN payloads to the same push endpoint."""

    def test_bigquery_transfer_payload_is_not_rtdn(self):
        payload = {
            "dataSourceId": "google_ads",
            "destinationDatasetId": "Google_Ads",
            "state": "FAILED",
        }
        assert is_google_play_rtdn_notification(payload) is False

    def test_subscription_notification_is_rtdn(self):
        payload = {
            "version": "1.0",
            "packageName": "com.example.app",
            "eventTimeMillis": "123",
            "subscriptionNotification": {
                "notificationType": 4,
                "purchaseToken": "abc",
            },
        }
        assert is_google_play_rtdn_notification(payload) is True
