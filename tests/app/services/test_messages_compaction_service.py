import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.agent import agent as agent_module
from app.core.config import global_config_loaded_from_config_yaml
from app.services import messages_compaction_service


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    async_session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
    await engine.dispose()


async def _delete_compaction_row(db: AsyncSession, key: str) -> None:
    await db.execute(
        text("DELETE FROM messages_compaction WHERE key = :key"),
        {"key": key},
    )
    await db.commit()


@pytest.mark.asyncio
async def test_messages_compaction_upsert_and_get(db_session: AsyncSession):
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
    key = f"{user_id}:{agent_id}"
    first_payload = {
        "source_session_id": str(uuid.uuid4()),
        "max_messages_limit": 5,
        "original_messages_count": 12,
        "compacted_messages_count": 2,
        "compacted_messages": [
            {
                "role": "user",
                "content": "hello from old session",
                "created_at": "2026-03-24T10:00:00+00:00",
            },
            {
                "role": "assistant",
                "content": "old assistant reply",
                "created_at": "2026-03-24T10:00:05+00:00",
            },
        ],
    }
    second_payload = {
        **first_payload,
        "original_messages_count": 20,
        "compacted_messages_count": 1,
        "compacted_messages": [
            {
                "role": "user",
                "content": "updated compacted text",
                "created_at": "2026-03-24T11:00:00+00:00",
            }
        ],
    }

    await _delete_compaction_row(db_session, key)
    try:
        sync_engine = agent_module.get_sync_engine()
        assert (
            messages_compaction_service.upsert_compaction_payload(
                sync_engine=sync_engine,
                user_id=user_id,
                agent_id=agent_id,
                payload=first_payload,
            )
            is True
        )
        loaded_first = messages_compaction_service.get_compaction_payload(
            sync_engine=sync_engine,
            user_id=user_id,
            agent_id=agent_id,
        )
        assert loaded_first is not None
        assert loaded_first["original_messages_count"] == 12
        assert loaded_first["compacted_messages_count"] == 2

        assert (
            messages_compaction_service.upsert_compaction_payload(
                sync_engine=sync_engine,
                user_id=user_id,
                agent_id=agent_id,
                payload=second_payload,
            )
            is True
        )
        loaded_second = messages_compaction_service.get_compaction_payload(
            sync_engine=sync_engine,
            user_id=user_id,
            agent_id=agent_id,
        )
        assert loaded_second is not None
        assert loaded_second["original_messages_count"] == 20
        assert loaded_second["compacted_messages_count"] == 1
        assert (
            loaded_second["compacted_messages"][0]["content"]
            == "updated compacted text"
        )
    finally:
        await _delete_compaction_row(db_session, key)
