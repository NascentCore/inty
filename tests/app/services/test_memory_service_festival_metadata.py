import importlib
import sys
import types
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest


def _load_memory_service_module():
    fake_agent_module = types.ModuleType("app.core.agent.agent")
    fake_agent_module.get_sync_engine = lambda: None

    fake_memory_module = types.ModuleType("app.models.memory")
    fake_memory_module.Memory = type("Memory", (), {})

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
    festival_name = _FakeColumn()
    festival_date = _FakeColumn()
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
        "festival_date": "2026-11-26",
    }


def test_build_festival_memory_metadata_includes_llm_when_provided():
    out = service.build_festival_memory_metadata(
        "Easter", date(2026, 4, 5), llm="mistralai/devstral-2512"
    )
    assert out.get("llm") == "mistralai/devstral-2512"
    assert "festival_name" in out
    assert "festival_data" in out


def test_build_festival_memory_metadata_omits_llm_when_none_or_empty():
    out_none = service.build_festival_memory_metadata("Xmas", date(2026, 12, 25), llm=None)
    assert "llm" not in out_none
    out_empty = service.build_festival_memory_metadata("New Year", date(2027, 1, 1), llm="")
    assert "llm" not in out_empty
    out_blank = service.build_festival_memory_metadata("Day", date(2027, 1, 2), llm="   ")
    assert "llm" not in out_blank


def test_resolve_festival_name_and_date_prefers_metadata():
    name, day = service.resolve_festival_name_and_date(
        {"festival_name": "New Year", "festival_data": "2026-01-01"},
        "Legacy New Year",
        date(2026, 1, 2),
    )
    assert name == "New Year"
    assert day == date(2026, 1, 1)


def test_resolve_festival_name_and_date_falls_back_to_legacy_columns():
    name, day = service.resolve_festival_name_and_date(
        None,
        "Legacy Festival",
        date(2026, 2, 2),
    )
    assert name == "Legacy Festival"
    assert day == date(2026, 2, 2)


@pytest.mark.asyncio
async def test_get_festival_memories_for_user_agent_reads_metadata_and_fallback():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    # row format:
    # (id, metadata, legacy_festival_name, legacy_festival_date, content)
    mock_result.fetchall.return_value = [
        (
            2,
            {"festival_name": "Christmas", "festival_data": "2026-12-25"},
            "Legacy Christmas",
            date(2026, 12, 24),
            "From metadata",
        ),
        (
            1,
            None,
            "Valentine",
            date(2026, 2, 14),
            "From legacy columns",
        ),
        (
            3,
            {"festival_name": "Broken", "festival_data": "bad-date"},
            None,
            None,
            "Should skip due to missing valid date",
        ),
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    service.Memory = _FakeMemory
    service.select = lambda *args, **kwargs: _DummyQuery()

    out = await service.get_festival_memories_for_user_agent(
        mock_db, "user-1", "agent-1"
    )

    assert out == [
        {
            "memory_id": 1,
            "festival_date": "2026-02-14",
            "festival_name": "Valentine",
            "memory": "From legacy columns",
        },
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
    mock_result.fetchall.return_value = [
        (
            8,
            {"festival_name": "Mother's Day", "festival_data": "2026-05-10"},
            None,
            None,
        ),
        (9, None, "Father's Day", date(2026, 6, 21)),
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    service.Memory = _FakeMemory
    service.select = lambda *args, **kwargs: _DummyQuery()

    out = await service.get_undelivered_festival_memories(mock_db, "u1", "a1")
    assert out == [
        {
            "id": 8,
            "festival_name": "Mother's Day",
            "festival_date": date(2026, 5, 10),
        },
        {
            "id": 9,
            "festival_name": "Father's Day",
            "festival_date": date(2026, 6, 21),
        },
    ]
