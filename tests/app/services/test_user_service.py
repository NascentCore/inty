import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import psycopg2
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import get_async_db
from app.models import Base
from app.models.user import AuthType, User
from app.services.subscription_service import SubscriptionService
from app.services.user_service import delete_user_account, generate_next_readable_id


class TestUserDeletion:
    """Test user deletion functionality"""

    @pytest.mark.asyncio
    async def test_delete_user_account_real_function(self):
        """Test the real delete_user_account function with async database"""
#创建异步数据库引擎
        engine = create_async_engine(global_config_loaded_from_config_yaml.database.async_url)
# 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
#创建异步会话
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
# 第1步：在数据库中创建具有唯一ID的测试用户
            user_id = f"user_test_real_function_{uuid.uuid4().hex[:8]}"
            readable_id = str(uuid.uuid4().int)[:8]
            test_user = User(
                id=user_id,
                readable_id=readable_id,
                auth_type=AuthType.GOOGLE,
                nickname="Test User Real Function",
                email=f"test_real_{uuid.uuid4().hex[:8]}@example.com",
                is_active=True,
                created_at=datetime.now(UTC),
            )

            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
# 验证用户创建成功
            user_query = select(User).where(User.id == user_id)
            result = await session.execute(user_query)
            created_user = result.scalar_one()

            assert created_user is not None
            assert created_user.id == user_id
            assert created_user.is_active is True
            assert created_user.deleted_at is None
            assert created_user.deletion_reason is None

            mock_subscription_service = AsyncMock(spec=SubscriptionService)
# 第二步：调用真正的delete_user_account函数
            deletion_result = await delete_user_account(
                db=session,
                user_id=user_id,
                subscription_service=mock_subscription_service,
                deletion_reason="Test deletion with real function",
            )
# 第三步：验证删除结果
            assert deletion_result["success"] is True
            assert deletion_result["message"] == "账户删除成功"
            assert deletion_result["user_id"] == user_id
#步骤4：验证数据库中的用户记录
            user_query = select(User).where(User.id == user_id)
            result = await session.execute(user_query)
            deleted_user = result.scalar_one()

            assert deleted_user is not None
            assert deleted_user.id == user_id
            assert deleted_user.is_active is False  # Should be marked as inactive
            assert deleted_user.deleted_at is not None  # Should have deletion timestamp
            assert deleted_user.deletion_reason == "Test deletion with real function"

            assert (
                mock_subscription_service.get_user_subscription_status.call_count == 1
            )
            assert (
                mock_subscription_service.cancel_user_subscriptions_for_deletion.call_count
                == 1
            )
# Clean up - 删除测试用户
            await session.delete(deleted_user)
            await session.commit()

        await engine.dispose()


async def test_generate_next_readable_id():
    """Test the generate_next_readable_id function"""
    async for async_session in get_async_db():
        readable_ids = []
        for i in range(10):
            readable_ids.append(await generate_next_readable_id(async_session))
        assert len(set(readable_ids)) == 10, "all readable ids should be unique"
