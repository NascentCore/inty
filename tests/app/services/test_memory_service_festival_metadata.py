import importlib
import sys
import types
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.types.llm_config import LLMConfig
from app.models.memory import FestivalMemoryMetadata as RealFestivalMemoryMetadata


def test_festival_memory_metadata_model_dump_for_db():
    """FestivalMemoryMetadata.model_dump_for_db 输出 festival_name、festival_data、可选 llm_config（无 festival_date key）。"""
    meta = RealFestivalMemoryMetadata(
        festival_name="Easter",
        festival_date="2026-04-05",
        llm_config=None,
    )
    out = meta.model_dump_for_db()
    assert out["festival_name"] == "Easter"
    assert out["festival_data"] == "2026-04-05"
    assert "festival_date" not in out
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
    out2 = meta_with_llm.model_dump_for_db()
    assert out2["festival_name"] == "Xmas"
    assert out2["festival_data"] == "2026-12-25"
    assert out2["llm_config"] == {
        "model": "openrouter/foo",
        "temperature": 0.0,
        "max_tokens": 2000,
    }


def test_festival_memory_metadata_model_validate_from_db():
    """FestivalMemoryMetadata.model_validate_from_db 仅读取 festival_name、festival_data、llm_config。"""
    meta = RealFestivalMemoryMetadata.model_validate_from_db(
        {"festival_name": "New Year", "festival_data": "2027-01-01"}
    )
    assert meta.festival_name == "New Year"
    assert meta.festival_date == "2027-01-01"
    assert meta.llm_config is None

    meta_with_llm = RealFestivalMemoryMetadata.model_validate_from_db(
        {
            "festival_name": "Valentine",
            "festival_data": "2027-02-14",
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

    empty = RealFestivalMemoryMetadata.model_validate_from_db({})
    assert empty.festival_name is None
    assert empty.festival_date is None
    assert empty.llm_config is None


def _load_memory_service_module():
    fake_agent_module = types.ModuleType("app.core.agent.agent")
    fake_agent_module.get_sync_engine = lambda: None

    fake_memory_module = types.ModuleType("app.models.memory")
    fake_memory_module.Memory = type("Memory", (), {})
    fake_memory_module.FestivalMemoryMetadata = RealFestivalMemoryMetadata

    fake_chat_history_module = types.ModuleType("app.services.chat_history_service")
    fake_chat_history_module.add_festival_memory_prompt_message_sync = lambda *args, **kwargs: None
    fake_chat_history_module.get_chat_history_connection = lambda: None
    fake_chat_history_module.get_festival_memory_prompt_content_for_agent_sync = (
        lambda *args, **kwargs: "prompt"
    )

    fake_chat_service_module = types.ModuleType("app.services.chat_service")
    fake_chat_service_module.generate_session_id = lambda chat_id: str(chat_id)

    sys.modules.pop("app.services.memory_service", None)
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "app.core.agent.agent", fake_agent_module)
        mp.setitem(sys.modules, "app.models.memory", fake_memory_module)
        mp.setitem(sys.modules, "app.services.chat_history_service", fake_chat_history_module)
        mp.setitem(sys.modules, "app.services.chat_service", fake_chat_service_module)
        module = importlib.import_module("app.services.memory_service")
    return module


service = _load_memory_service_module()


class _FakeColumn:
    def __eq__(self, _other):
        return self

    def is_(self, _other):
        return self


class _FakeMemory:
    id = _FakeColumn()
    user_id = _FakeColumn()
    agent_id = _FakeColumn()
    memory_type = _FakeColumn()
    meta_data = _FakeColumn()
    content = _FakeColumn()
    delivery_at = _FakeColumn()
    system_notification_sent_at = _FakeColumn()


class _DummyQuery:
    def where(self, *_args, **_kwargs):
        return self


def test_build_festival_memory_metadata_contains_required_keys():
    out = service.build_festival_memory_metadata("Thanksgiving", date(2026, 11, 26))
    assert out == {
        "festival_name": "Thanksgiving",
        "festival_data": "2026-11-26",
    }


def test_build_festival_memory_metadata_includes_llm_config_when_provided():
    llm_config = {
        "model": "mistralai/devstral-2512",
        "temperature": 0.0,
        "max_tokens": 2000,
    }
    out = service.build_festival_memory_metadata(
        "Easter", date(2026, 4, 5), llm_config=llm_config
    )
    assert out.get("llm_config") == llm_config
    assert "festival_name" in out
    assert "festival_data" in out


def test_build_festival_memory_metadata_omits_llm_config_when_none_or_empty_model():
    out_none = service.build_festival_memory_metadata(
        "Xmas", date(2026, 12, 25), llm_config=None
    )
    assert "llm_config" not in out_none
    out_empty = service.build_festival_memory_metadata(
        "New Year", date(2027, 1, 1), llm_config={}
    )
    assert "llm_config" not in out_empty
    out_blank = service.build_festival_memory_metadata(
        "Day", date(2027, 1, 2), llm_config={"model": "   "}
    )
    assert "llm_config" not in out_blank


def test_metadata_to_llm_config_output_from_llm_config():
    """metadata 含 llm_config（dict）时返回其规范化副本。"""
    meta = {
        "festival_name": "X",
        "llm_config": {
            "model": "google/gemini-2.5-flash-lite",
            "temperature": 0.0,
            "max_tokens": 2000,
        },
    }
    out = service.metadata_to_llm_config_output(meta)
    assert out == {
        "model": "google/gemini-2.5-flash-lite",
        "temperature": 0.0,
        "max_tokens": 2000,
    }


def test_metadata_to_llm_config_output_none_when_no_llm_config():
    """metadata 无 llm_config 时返回 None（不再支持 legacy llm 字符串）。"""
    assert service.metadata_to_llm_config_output({"festival_name": "X"}) is None


def test_metadata_to_llm_config_output_none_when_neither():
    """metadata 无 llm_config 且无 llm 时返回 None。"""
    assert service.metadata_to_llm_config_output({}) is None
    assert service.metadata_to_llm_config_output({"festival_name": "Y"}) is None


def test_resolve_festival_name_and_date_from_metadata():
    name, day = service.resolve_festival_name_and_date(
        {"festival_name": "New Year", "festival_data": "2026-01-01"},
    )
    assert name == "New Year"
    assert day == date(2026, 1, 1)


@pytest.mark.asyncio
async def test_get_festival_memories_for_user_agent_reads_metadata():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    # row format: (id, metadata, content)
    mock_result.fetchall.return_value = [
        (
            2,
            {"festival_name": "Christmas", "festival_data": "2026-12-25"},
            "From metadata",
        ),
        (
            1,
            None,
            "From legacy columns",
        ),
        (
            3,
            {"festival_name": "Broken", "festival_data": "bad-date"},
            "Should skip due to missing valid date",
        ),
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    service.Memory = _FakeMemory
    service.select = lambda *args, **kwargs: _DummyQuery()

    out = await service.get_festival_memories_for_user_agent(
        mock_db, "user-1", "agent-1"
    )

    # Rows with None metadata or invalid date are skipped; only metadata with valid date.
    assert out == [
        {
            "memory_id": 2,
            "festival_date": "2026-12-25",
            "festival_name": "Christmas",
            "memory": "From metadata",
        },
    ]


@pytest.mark.asyncio
async def test_get_undelivered_festival_memories_reads_metadata():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    # row format: (id, metadata)
    mock_result.fetchall.return_value = [
        (
            8,
            {"festival_name": "Mother's Day", "festival_data": "2026-05-10"},
        ),
        (9, None),
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    service.Memory = _FakeMemory
    service.select = lambda *args, **kwargs: _DummyQuery()

    out = await service.get_undelivered_festival_memories(mock_db, "u1", "a1")
    # Row with None metadata yields (None, None) and is skipped.
    assert out == [
        {
            "id": 8,
            "festival_name": "Mother's Day",
            "festival_date": date(2026, 5, 10),
        },
    ]
