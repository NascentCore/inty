# CREATED_BY_AGENT
"""
Integration test for deliver_festival_memories_for_user_agent.

Uses real DB (config.yaml). Asserts that after calling deliver_festival_memories_for_user_agent:
- memory.delivery_at is set
- chat_history has exactly one row for that session with festival_memory_prompt and matching festivalMemoryId
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import Agent, AgentStatus
from app.models.chat import Chat
from app.models.chat_history import ChatHistory
from app.models.memory import Memory
from app.models.user import AuthType, Gender, User
from app.services.chat_service import generate_session_id
from app.services.memory_service import deliver_festival_memories_for_user_agent


@pytest.fixture
def sync_db_session():
    """Sync session for setup, assertions and cleanup; same DB as E2E."""
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
async def async_db_session():
    """Async session for calling deliver_festival_memories_for_user_agent."""
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


@pytest.mark.asyncio
async def test_deliver_festival_memories_for_user_agent_writes_chat_history_and_sets_delivery_at(
    sync_db_session,
    async_db_session: AsyncSession,
):
    """
    Integration: create user, agent, chat, memory (delivery_at=None);
    call deliver_festival_memories_for_user_agent; assert memory.delivery_at set
    and chat_history has one festival_memory_prompt row for that memory.
    """
    user_id = f"user-{uuid.uuid4().hex[:12]}"
    agent_id = str(uuid.uuid4())
    chat_id = str(uuid.uuid4())
    festival_name = "IntegrationTestFest"
    festival_date = date.today()

    user = User(
        id=user_id,
        auth_type=AuthType.GUEST,
        device_id=f"device-{uuid.uuid4().hex[:12]}",
    )
    agent = Agent(
        id=agent_id,
        name="Integration Test Agent",
        gender=Gender.FEMALE,
        status=AgentStatus.APPROVED,
        creator_id=user_id,
    )
    chat = Chat(
        id=chat_id,
        user_id=user_id,
        agent_id=agent_id,
        is_active=True,
    )
    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="festival",
        content="Integration test festival memory content",
        meta_data={
            "festival_name": festival_name,
            "festival_date": festival_date.isoformat(),
        },
        extracted_at=datetime.now(timezone.utc),
        delivery_at=None,
    )

    sync_db_session.add(user)
    sync_db_session.flush()
    sync_db_session.add(agent)
    sync_db_session.flush()
    sync_db_session.add(chat)
    sync_db_session.flush()
    sync_db_session.add(memory)
    sync_db_session.commit()
    sync_db_session.refresh(memory)
    memory_id = memory.id
    session_id = generate_session_id(chat_id)

    session_uuid = uuid.UUID(session_id)
    chat_history_filter = (
        ChatHistory.session_id == session_uuid,
        ChatHistory.deleted_at.is_(None),
        ChatHistory.meta_data["messageType"].astext == "festival_memory_prompt",
        ChatHistory.meta_data["festivalMemoryId"].astext == str(memory_id),
    )
    try:
        await deliver_festival_memories_for_user_agent(
            async_db_session, user_id, agent_id
        )

        # Assert memory.delivery_at set
        sync_db_session.refresh(memory)
        assert (
            memory.delivery_at is not None
        ), "memory.delivery_at should be set after delivery"

        # Assert chat_history: exactly one row for this session + festival_memory_prompt + this memory
        stmt = select(ChatHistory).where(*chat_history_filter)
        result = sync_db_session.execute(stmt)
        rows = result.scalars().all()
        assert len(rows) == 1, (
            f"Expected exactly one chat_history row for session_id={session_id}, "
            f"messageType=festival_memory_prompt, festivalMemoryId={memory_id}, got {len(rows)}"
        )
        row0 = rows[0]
        assert row0.meta_data.get("festivalName") == festival_name
        assert row0.meta_data.get("festivalDate") == festival_date.isoformat()
    finally:
        # Remove chat_history row created by delivery so test leaves no orphan rows
        sync_db_session.execute(delete(ChatHistory).where(*chat_history_filter))
        sync_db_session.delete(memory)
        sync_db_session.delete(chat)
        sync_db_session.delete(agent)
        sync_db_session.delete(user)
        sync_db_session.commit()
