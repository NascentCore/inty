"""
端到端测试：Email + Password 登录功能

测试后端服务的 email + password 登录功能，包括：
- 成功的登录流程
- 错误处理（错误的密码、不存在的用户、无效的 email 格式）
- Token 验证和使用
"""

import os
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.core.security import get_password_hash
from app.core.uuid import get_new_user_id
from app.models.agent import Agent
from app.models.user import AuthType, User
from app.services.user_service import generate_next_readable_id
from tests.app.api.test_client import TestClient

API_BASE_URL = os.getenv("INTY_API_BASE_URL", "http://localhost:8000")


@pytest.fixture
async def db_session():
    """提供数据库会话用于测试"""
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


@pytest.fixture
async def test_user_with_password(db_session: AsyncSession):
    """创建带密码的测试用户"""
    user_id = get_new_user_id()
    readable_id = await generate_next_readable_id(db_session)
    test_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    test_password = "TestPassword123!"
    hashed_password = get_password_hash(test_password)

    user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.EMAIL,
        email=test_email,
        password=hashed_password,
        nickname=f"Test User {uuid.uuid4().hex[:6]}",
        system_language="en",
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    yield {
        "user": user,
        "email": test_email,
        "password": test_password,
    }

    # 清理：先删除用户创建的所有 agent，避免外键约束问题。
    # 使用 Core delete：Agent 有 version 乐观锁，HTTP 测试已在服务端改过 version，
    # ORM delete 会带旧 version 条件导致 StaleDataError。
    await db_session.execute(delete(Agent).where(Agent.creator_id == user.id))

    # 然后删除测试用户
    user.deleted_at = None  # 确保可以查询到
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_email_password_login_success(
    test_user_with_password: dict, db_session: AsyncSession
):
    """测试成功的 email + password 登录"""
    client = TestClient(API_BASE_URL)

    try:
        email = test_user_with_password["email"]
        password = test_user_with_password["password"]

        # 调用登录接口
        response = client.client.post(
            f"{API_BASE_URL}/api/v1/auth/google/login",
            json={
                "email": email,
                "password": password,
            },
        )

        # 验证响应
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert data.get("code") == 200, f"Login returned error: {data}"

        # 验证返回的数据结构
        login_data = data.get("data")
        assert login_data is not None, "Login response missing data"
        assert "token" in login_data, "Login response missing token"
        assert "user" in login_data, "Login response missing user"

        # 验证 token
        token = login_data["token"]
        assert token is not None and len(token) > 0, "Token is empty"

        # 验证用户信息
        user_info = login_data["user"]
        assert user_info["id"] == test_user_with_password["user"].id
        assert user_info["email"] == email
        assert user_info["auth_type"] == AuthType.EMAIL.value
        assert user_info["is_new_user"] is False

        # 验证 token 可以用于后续 API 调用
        client.token = token
        client.client.headers.update({"Authorization": f"Bearer {token}"})

        # 尝试获取用户信息
        profile_response = client.client.get(f"{API_BASE_URL}/api/v1/users/me")
        assert profile_response.status_code == 200, "Token validation failed"
        profile_data = profile_response.json()
        assert profile_data.get("code") == 200
        assert profile_data["data"]["id"] == test_user_with_password["user"].id

        # 尝试创建 agent 来验证 token 有效性
        create_agent_response = client.create_agent(
            name="Test Agent",
            gender="FEMALE",
            visibility="PUBLIC",
            personality="Test Agent Personality",
            scenario="Test Agent Scenario",
        )
        assert create_agent_response is not None, "Create agent failed"

    finally:
        client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_email_password_login_wrong_password(
    test_user_with_password: dict,
):
    """测试错误的密码登录"""
    client = TestClient(API_BASE_URL)

    try:
        email = test_user_with_password["email"]
        wrong_password = "WrongPassword123!"

        # 调用登录接口
        response = client.client.post(
            f"{API_BASE_URL}/api/v1/auth/google/login",
            json={
                "email": email,
                "password": wrong_password,
            },
        )

        # 验证响应
        assert response.status_code == 200, f"Login request failed: {response.text}"
        data = response.json()
        assert data.get("code") != 200, "Login should have failed with wrong password"
        assert "Invalid Email password combination" in data.get("message", "")

    finally:
        client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_email_password_login_nonexistent_user():
    """测试不存在的用户登录"""
    client = TestClient(API_BASE_URL)

    try:
        nonexistent_email = f"nonexistent-{uuid.uuid4().hex[:8]}@example.com"
        password = "SomePassword123!"

        # 调用登录接口
        response = client.client.post(
            f"{API_BASE_URL}/api/v1/auth/google/login",
            json={
                "email": nonexistent_email,
                "password": password,
            },
        )

        # 验证响应
        assert response.status_code == 200, f"Login request failed: {response.text}"
        data = response.json()
        assert data.get("code") != 200, "Login should have failed for nonexistent user"
        assert "Invalid Email password combination" in data.get("message", "")

    finally:
        client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_email_password_login_invalid_email_format():
    """测试无效的 email 格式"""
    client = TestClient(API_BASE_URL)

    try:
        invalid_email = "not-an-email"
        password = "SomePassword123!"

        # 调用登录接口
        response = client.client.post(
            f"{API_BASE_URL}/api/v1/auth/google/login",
            json={
                "email": invalid_email,
                "password": password,
            },
        )

        # 验证响应
        assert response.status_code == 200, f"Login request failed: {response.text}"
        data = response.json()
        assert data.get("code") != 200, "Login should have failed for invalid email"
        assert "Invalid email format" in data.get("message", "")

    finally:
        client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_email_password_login_missing_fields():
    """测试缺少必要字段的登录请求"""
    client = TestClient(API_BASE_URL)

    try:
        # 测试缺少 password
        response = client.client.post(
            f"{API_BASE_URL}/api/v1/auth/google/login",
            json={
                "email": "test@example.com",
            },
        )

        # 验证响应（应该被 Pydantic 验证拒绝）
        assert response.status_code in (200, 422), f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert data.get("code") != 200, "Login should have failed without password"

        # 测试缺少 email
        response = client.client.post(
            f"{API_BASE_URL}/api/v1/auth/google/login",
            json={
                "password": "SomePassword123!",
            },
        )

        # 验证响应
        assert response.status_code in (200, 422), f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert data.get("code") != 200, "Login should have failed without email"

    finally:
        client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_email_password_login_user_without_password(
    db_session: AsyncSession,
):
    """测试没有设置密码的用户登录"""
    client = TestClient(API_BASE_URL)

    # 创建没有密码的用户
    user_id = get_new_user_id()
    readable_id = await generate_next_readable_id(db_session)
    test_email = f"no-password-{uuid.uuid4().hex[:8]}@example.com"

    user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.EMAIL,
        email=test_email,
        password=None,  # 没有设置密码
        nickname=f"Test User {uuid.uuid4().hex[:6]}",
        system_language="en",
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    try:
        # 尝试登录
        response = client.client.post(
            f"{API_BASE_URL}/api/v1/auth/google/login",
            json={
                "email": test_email,
                "password": "SomePassword123!",
            },
        )

        # 验证响应
        assert response.status_code == 200, f"Login request failed: {response.text}"
        data = response.json()
        assert data.get("code") != 200, "Login should have failed for user without password"
        assert "Invalid Email password combination" in data.get("message", "")

    finally:
        # 清理
        await db_session.delete(user)
        await db_session.commit()
        client.close()
