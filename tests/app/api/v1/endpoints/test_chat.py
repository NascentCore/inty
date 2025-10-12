"""
Integration tests for chat endpoints.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.api import deps
from app.main import app
from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.models.user import AuthType, Gender, User
from app.schemas.chat import ChatCompletionRequest, ChatMessage


@pytest.fixture
async def test_db_session():
    """Create test database session with test data."""
    # Create async database engine
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:sxwl666!@localhost:5432/inty"
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    
    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Create test user
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        test_user = models.User(
            id=user_id,
            readable_id=f"u{uuid.uuid4().hex[:7]}",
            auth_type=AuthType.PHONE,
            nickname="Test User",
            email="test@example.com",
            system_language="en",
            is_active=True,
        )
        session.add(test_user)
        
        # Create test agent
        agent_id = f"test-agent-{uuid.uuid4().hex[:8]}"
        test_agent = models.Agent(
            id=agent_id,
            readable_id=f"a{uuid.uuid4().hex[:7]}",
            name="Test Agent",
            gender=Gender.FEMALE,
            avatar="https://example.com/avatar.jpg",
            intro="Test agent for integration testing",
            opening="Hello! I'm a test agent.",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
            main_prompt="You are a helpful test assistant.",
        )
        session.add(test_agent)
        
        await session.commit()
        await session.refresh(test_user)
        await session.refresh(test_agent)
        
        yield session, test_user, test_agent
    
    # Cleanup
    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_chat_completions_happy_case(test_db_session):
    """Test successful chat completion with agent."""
    session, test_user, test_agent = test_db_session

    # Create test client
    client = TestClient(app)

    # Prepare request data
    request_data = ChatCompletionRequest(
        messages=[ChatMessage(role="user", content="Hello, how are you?")],
        stream=False,
        model="chatbot",
        language="en",
    )

    # Override the dependency for this test
    def override_get_current_active_user():
        return test_user

    def override_get_async_db():
        return session

    app.dependency_overrides[deps.get_current_active_user] = (
        override_get_current_active_user
    )
    app.dependency_overrides[deps.get_async_db] = override_get_async_db

    try:
        # Make request
        response = client.post(
            f"/api/v1/chat/completions/{test_agent.id}", json=request_data.dict()
        )
    finally:
        # Clean up the override
        app.dependency_overrides.clear()

    # Assertions
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["code"] == 200
    assert "data" in response_data

    data = response_data["data"]
    assert data["object"] == "chat.completion"
    assert "choices" in data
    assert len(data["choices"]) == 1

    choice = data["choices"][0]
    assert choice["index"] == 0
    assert choice["finish_reason"] == "stop"
    assert "message" in choice

    message = choice["message"]
    assert message["role"] == "assistant"
    assert message["content"] is not None
    assert len(message["content"]) > 0
    assert "id" in message
    assert "timestamp" in message
