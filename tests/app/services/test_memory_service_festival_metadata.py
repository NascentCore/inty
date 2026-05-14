"""
app.services.memory_service 的测试（节日元数据及相关辅助逻辑）。

使用真实 memory_service 与真实 DB，不做 patch。
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.types.llm_config import LLMConfig
from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import Agent, AgentStatus, Gender
from app.models.memory import FestivalMemoryMetadata as RealFestivalMemoryMetadata
from app.models.memory import Memory
from app.models.user import AuthType, User
from app.services import memory_service


@pytest.fixture
async def db_session():
    """Async session for real DB tests; same pattern as test_chat_image_generation."""
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


def test_festival_memory_metadata_dump_exclude_none():
    """FestivalMemoryMetadata.model_dump(exclude_none=True) 输出 festival_name、festival_date、可选 llm_config（无 festival_data key）。"""
    meta = RealFestivalMemoryMetadata(
        festival_name="Easter",
        festival_date="2026-04-05",
        llm_config=None,
    )
    out = meta.model_dump(exclude_none=True)
    assert out["festival_name"] == "Easter"
    assert out["festival_date"] == "2026-04-05"
    assert "festival_data" not in out
    assert "llm_config" not in out

    meta_with_llm = RealFestivalMemoryMetadata(
        festival_name="Xmas",
        festival_date="2026-12-25",
        llm_config=LLMConfig(
            model="openrouter/foo",
            temperature=0.0,
            max_tokens=2000,
        ),
    )
    out2 = meta_with_llm.model_dump(exclude_none=True)
    assert out2["festival_name"] == "Xmas"
    assert out2["festival_date"] == "2026-12-25"
    assert "llm_config" in out2
    assert out2["llm_config"]["model"] == "openrouter/foo"
    assert out2["llm_config"]["temperature"] == 0.0
    assert out2["llm_config"]["max_tokens"] == 2000


def test_festival_memory_metadata_model_validate():
    """FestivalMemoryMetadata.model_validate 读取 festival_name、festival_date、llm_config。"""
    meta = RealFestivalMemoryMetadata.model_validate(
        {"festival_name": "New Year", "festival_date": "2027-01-01"}
    )
    assert meta.festival_name == "New Year"
    assert meta.festival_date == "2027-01-01"
    assert meta.llm_config is None

    meta_with_llm = RealFestivalMemoryMetadata.model_validate(
        {
            "festival_name": "Valentine",
            "festival_date": "2027-02-14",
            "llm_config": {
                "model": "mistralai/devstral-2512",
                "temperature": 0.0,
                "max_tokens": 2000,
            },
        }
    )
    assert meta_with_llm.festival_name == "Valentine"
    assert meta_with_llm.festival_date == "2027-02-14"
    assert meta_with_llm.llm_config is not None
    assert meta_with_llm.llm_config.model == "mistralai/devstral-2512"
    assert meta_with_llm.llm_config.temperature == 0.0
    assert meta_with_llm.llm_config.max_tokens == 2000

    empty = RealFestivalMemoryMetadata.model_validate({})
    assert empty.festival_name is None
    assert empty.festival_date is None
    assert empty.llm_config is None


def test_build_festival_memory_metadata_contains_required_keys():
    out = memory_service.build_festival_memory_metadata(
        "Thanksgiving", date(2026, 11, 26)
    )
    assert out == {
        "festival_name": "Thanksgiving",
        "festival_date": "2026-11-26",
    }


def test_build_festival_memory_metadata_includes_llm_config_when_provided():
    llm_config = {
        "model": "mistralai/devstral-2512",
        "temperature": 0.0,
        "max_tokens": 2000,
    }
    out = memory_service.build_festival_memory_metadata(
        "Easter", date(2026, 4, 5), llm_config=llm_config
    )
    assert "festival_name" in out
    assert "festival_date" in out
    assert "llm_config" in out
    assert out["llm_config"]["model"] == "mistralai/devstral-2512"
    assert out["llm_config"]["temperature"] == 0.0
    assert out["llm_config"]["max_tokens"] == 2000


def test_build_festival_memory_metadata_omits_llm_config_when_none_or_empty_model():
    out_none = memory_service.build_festival_memory_metadata(
        "Xmas", date(2026, 12, 25), llm_config=None
    )
    assert "llm_config" not in out_none
    out_empty = memory_service.build_festival_memory_metadata(
        "New Year", date(2027, 1, 1), llm_config={}
    )
    assert "llm_config" not in out_empty
    out_blank = memory_service.build_festival_memory_metadata(
        "Day", date(2027, 1, 2), llm_config={"model": "   "}
    )
    assert "llm_config" not in out_blank


def test_metadata_to_llm_config_output_from_llm_config():
    """metadata 含 llm_config（dict）时返回完整 model_dump（含默认值）。"""
    meta = {
        "festival_name": "X",
        "llm_config": {
            "model": "google/gemini-2.5-flash-lite",
            "temperature": 0.0,
            "max_tokens": 2000,
        },
    }
    out = memory_service.metadata_to_llm_config_output(meta)
    assert out is not None
    assert out["model"] == "google/gemini-2.5-flash-lite"
    assert out["temperature"] == 0.0
    assert out["max_tokens"] == 2000


def test_metadata_to_llm_config_output_none_when_neither():
    """metadata 无 llm_config 且无 llm 时返回 None。"""
    assert memory_service.metadata_to_llm_config_output({}) is None
    assert memory_service.metadata_to_llm_config_output({"festival_name": "Y"}) is None


def test_resolve_festival_name_and_date_from_metadata():
    name, day = memory_service.resolve_festival_name_and_date(
        {"festival_name": "New Year", "festival_date": "2026-01-01"},
    )
    assert name == "New Year"
    assert day == date(2026, 1, 1)


@pytest.mark.asyncio
async def test_get_festival_memories_for_user_agent_reads_metadata(
    db_session: AsyncSession,
):
    """Real DB: create User, Agent, 3 Memory rows; only valid metadata row is returned."""
    user_id = f"user-{uuid.uuid4().hex[:12]}"
    agent_id = str(uuid.uuid4())

    user = User(
        id=user_id,
        auth_type=AuthType.GUEST,
        device_id=f"device-{uuid.uuid4().hex[:12]}",
    )
    agent = Agent(
        id=agent_id,
        name="Festival Metadata Test Agent",
        gender=Gender.FEMALE,
        status=AgentStatus.APPROVED,
        creator_id=user_id,
    )

    db_session.add(user)
    db_session.add(agent)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    m1 = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type=memory_service.MEMORY_TYPE_FESTIVAL,
        content="From metadata",
        meta_data={"festival_name": "Christmas", "festival_date": "2026-12-25"},
        extracted_at=now,
    )
    m2 = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type=memory_service.MEMORY_TYPE_FESTIVAL,
        content="From legacy columns",
        meta_data=None,
        extracted_at=now,
    )
    m3 = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type=memory_service.MEMORY_TYPE_FESTIVAL,
        content="Should skip due to missing valid date",
        meta_data={"festival_name": "Broken", "festival_date": "bad-date"},
        extracted_at=now,
    )
    db_session.add_all([m1, m2, m3])
    await db_session.commit()
    await db_session.refresh(m1)

    try:
        out = await memory_service.get_festival_memories_for_user_agent(
            db_session, user_id, agent_id
        )
        assert out == [
            {
                "memory_id": m1.id,
                "festival_date": "2026-12-25",
                "festival_name": "Christmas",
                "memory": "From metadata",
            },
        ]
    finally:
        await db_session.execute(delete(Memory).where(Memory.user_id == user_id))
        await db_session.execute(delete(Agent).where(Agent.id == agent_id))
        await db_session.execute(delete(User).where(User.id == user_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_get_undelivered_festival_memories_reads_metadata(
    db_session: AsyncSession,
):
    """Real DB: create User, Agent, 2 Memory rows (delivery_at=None); only valid metadata row is returned."""
    user_id = f"user-{uuid.uuid4().hex[:12]}"
    agent_id = str(uuid.uuid4())

    user = User(
        id=user_id,
        auth_type=AuthType.GUEST,
        device_id=f"device-{uuid.uuid4().hex[:12]}",
    )
    agent = Agent(
        id=agent_id,
        name="Undelivered Festival Test Agent",
        gender=Gender.FEMALE,
        status=AgentStatus.APPROVED,
        creator_id=user_id,
    )
    db_session.add(user)
    db_session.add(agent)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    m1 = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type=memory_service.MEMORY_TYPE_FESTIVAL,
        content="Mother's Day content",
        meta_data={"festival_name": "Mother's Day", "festival_date": "2026-05-10"},
        extracted_at=now,
        delivery_at=None,
    )
    m2 = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type=memory_service.MEMORY_TYPE_FESTIVAL,
        content="No metadata",
        meta_data=None,
        extracted_at=now,
        delivery_at=None,
    )
    db_session.add_all([m1, m2])
    await db_session.commit()
    await db_session.refresh(m1)

    try:
        out = await memory_service.get_undelivered_festival_memories(
            db_session, user_id, agent_id
        )
        assert out == [
            {
                "id": m1.id,
                "festival_name": "Mother's Day",
                "festival_date": date(2026, 5, 10),
            },
        ]
    finally:
        await db_session.execute(delete(Memory).where(Memory.user_id == user_id))
        await db_session.execute(delete(Agent).where(Agent.id == agent_id))
        await db_session.execute(delete(User).where(User.id == user_id))
        await db_session.commit()
