"""Integration tests for user account deletion endpoint."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.subscription import (
    SubscriptionPlan,
    SubscriptionPlanType,
    SubscriptionStatus,
    UserSubscription,
)
from app.models.user import User
from tests.app.api.test_client import TestClient


@pytest.fixture
async def db_session():
    """Provide a database session for testing."""
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )

    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.noci
def test_delete_account_success(integration_client: TestClient):
    """Test successful account deletion."""
    # Create a separate user for this test
    test_client = TestClient(integration_client.base_url)
    token = test_client.create_user()

    # Verify user exists and can access profile
    response = test_client.client.get(
        f"{test_client.base_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user_data = response.json()["data"]
    user_id = user_data["id"]

    # Delete the account
    delete_response = test_client.client.post(
        f"{test_client.base_url}/api/v1/users/delete-account",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["code"] == 200
    assert delete_data["data"]["success"] is True
    assert delete_data["data"]["message"] == "账户删除成功"
    assert delete_data["data"]["user_id"] == user_id

    # Verify user can no longer access profile (should fail authentication)
    # Note: Returns 400/401 because deleted_at 已被设置，账号视为已删除
    profile_response = test_client.client.get(
        f"{test_client.base_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code in (400, 401)


@pytest.mark.asyncio
async def test_delete_account_with_active_subscription(
    integration_client: TestClient, db_session: AsyncSession
):
    """Test account deletion fails when user has active subscription."""
    # Create a separate user for this test
    test_client = TestClient(integration_client.base_url)
    token = test_client.create_user()

    # Get user ID
    response = test_client.client.get(
        f"{test_client.base_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user_data = response.json()["data"]
    user_id = user_data["id"]

    # Create a test subscription plan
    plan_id = f"plan_test_{uuid.uuid4().hex[:8]}"
    test_plan = SubscriptionPlan(
        id=plan_id,
        name="Test Plan",
        description="Test subscription plan for deletion test",
        plan_type=SubscriptionPlanType.MONTHLY,
        price=9.99,
        currency="USD",
        google_play_product_id=f"test_product_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(test_plan)

    # Create an active subscription for the user
    subscription_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    active_subscription = UserSubscription(
        id=subscription_id,
        user_id=user_id,
        plan_id=plan_id,
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime.now(timezone.utc) - timedelta(days=10),
        end_date=datetime.now(timezone.utc) + timedelta(days=20),
    )
    db_session.add(active_subscription)
    await db_session.commit()

    # Try to delete the account - should fail
    delete_response = test_client.client.post(
        f"{test_client.base_url}/api/v1/users/delete-account",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["code"] != 200 or delete_data["data"]["success"] is False
    error_message = delete_data.get("message") or delete_data.get(
        "data", {}
    ).get("message", "")
    assert "订阅" in error_message or "subscription" in error_message.lower()

    # Clean up
    await db_session.delete(active_subscription)
    await db_session.delete(test_plan)
    await db_session.commit()
    test_client.close()


@pytest.mark.asyncio
async def test_delete_account_already_deleted(
    integration_client: TestClient, db_session: AsyncSession
):
    """Test deleting an already deleted account."""
    # Create a separate user for this test
    test_client = TestClient(integration_client.base_url)
    token = test_client.create_user()

    # Get user ID
    response = test_client.client.get(
        f"{test_client.base_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user_data = response.json()["data"]
    user_id = user_data["id"]

    # Manually mark user as deleted in database
    stmt = select(User).where(User.id == user_id)
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    user.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Try to delete the account again - should fail
    delete_response = test_client.client.post(
        f"{test_client.base_url}/api/v1/users/delete-account",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["code"] != 200 or delete_data["data"]["success"] is False
    error_message = delete_data.get("message") or delete_data.get(
        "data", {}
    ).get("message", "")
    assert "删除" in error_message or "deleted" in error_message.lower()

    # Clean up
    test_client.close()


def test_delete_account_with_reason(integration_client: TestClient):
    """Test account deletion with a custom deletion reason."""
    # Create a separate user for this test
    test_client = TestClient(integration_client.base_url)
    token = test_client.create_user()

    # Get user ID
    response = test_client.client.get(
        f"{test_client.base_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user_data = response.json()["data"]
    user_id = user_data["id"]

    # Delete the account with a custom reason
    deletion_reason = "测试删除原因"
    delete_response = test_client.client.post(
        f"{test_client.base_url}/api/v1/users/delete-account",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": deletion_reason},
    )

    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["code"] == 200
    assert delete_data["data"]["success"] is True
    assert delete_data["data"]["message"] == "账户删除成功"
    assert delete_data["data"]["user_id"] == user_id

    # Verify user can no longer access profile
    # Note: Returns 400/401 because deleted_at 被设置后会阻止认证
    profile_response = test_client.client.get(
        f"{test_client.base_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code in (400, 401)

    test_client.close()
