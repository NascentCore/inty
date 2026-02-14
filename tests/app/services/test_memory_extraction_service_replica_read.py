import importlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import pytest


def _load_memory_extraction_service_module():
    fake_config = types.SimpleNamespace(
        database=types.SimpleNamespace(
            url="postgresql://primary-host:5432/inty",
            async_replica_url="postgresql+asyncpg://replica-host:5432/inty",
        ),
        memory_extraction=types.SimpleNamespace(
            trigger_new_user_messages=30,
            trigger_incremental_messages=30,
            model="",
        ),
    )
    fake_core_config_module = types.ModuleType("app.core.config")
    fake_core_config_module.global_config_loaded_from_config_yaml = fake_config

    fake_memory_model_module = types.ModuleType("app.models.memory")
    fake_memory_model_module.Memory = type("Memory", (), {})
    fake_memory_model_module.MemoryExtractionLog = type("MemoryExtractionLog", (), {})

    fake_chat_history_module = types.ModuleType("app.services.chat_history_service")
    fake_chat_history_module.get_chat_history_connection = lambda: None
    fake_chat_history_module.get_chat_history_replica_connection = lambda: None

    fake_chat_service_module = types.ModuleType("app.services.chat_service")
    fake_chat_service_module.generate_session_id = lambda chat_id: f"session-{chat_id}"

    fake_openrouter_module = types.ModuleType("app.utils.openrouter_memory")
    fake_openrouter_module.DEFAULT_MEMORY_EXTRACTION_MODEL = "mistralai/devstral-2512"

    async def _dummy_openrouter_call(*args, **kwargs):
        return ("dummy", None, None)

    fake_openrouter_module.call_openrouter_for_extraction = _dummy_openrouter_call

    sys.modules.pop("app.services.memory_extraction_service", None)
    with patch.dict(
        sys.modules,
        {
            "app.core.config": fake_core_config_module,
            "app.models.memory": fake_memory_model_module,
            "app.services.chat_history_service": fake_chat_history_module,
            "app.services.chat_service": fake_chat_service_module,
            "app.utils.openrouter_memory": fake_openrouter_module,
        },
    ):
        return importlib.import_module("app.services.memory_extraction_service")


service = _load_memory_extraction_service_module()


class _FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params):
        self._conn.executed.append((query, params))

    def fetchall(self):
        result = self._conn.fetchall_results[self._conn.fetchall_index]
        self._conn.fetchall_index += 1
        return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self, fetchall_results):
        self.fetchall_results = fetchall_results
        self.fetchall_index = 0
        self.executed = []

    def cursor(self):
        return _FakeCursor(self)


def test_get_all_messages_for_user_prefers_replica_connection():
    replica_conn = _FakeConnection(
        fetchall_results=[
            [("chat-1",)],
            [
                ({"type": "human", "data": {"content": "hi"}},),
                ({"type": "ai", "data": {"content": "hello"}},),
            ],
        ]
    )

    with (
        patch.object(
            service,
            "get_chat_history_replica_connection",
            return_value=replica_conn,
        ) as mock_replica_conn,
        patch.object(service, "get_chat_history_connection") as mock_primary_conn,
        patch.object(
            service,
            "generate_session_id",
            side_effect=lambda chat_id: f"session-{chat_id}",
        ),
    ):
        rows = service.get_all_messages_for_user("user-1", prefer_replica_read=True)

    assert rows == [("user", "hi"), ("assistant", "hello")]
    mock_replica_conn.assert_called_once()
    mock_primary_conn.assert_not_called()


def test_get_all_messages_for_user_fallbacks_to_primary_when_replica_fails():
    primary_conn = _FakeConnection(
        fetchall_results=[
            [("chat-1",)],
            [
                ({"type": "human", "data": {"content": "fallback"}},),
            ],
        ]
    )

    with (
        patch.object(
            service,
            "get_chat_history_replica_connection",
            side_effect=psycopg.OperationalError("replica not available"),
        ),
        patch.object(
            service,
            "get_chat_history_connection",
            return_value=primary_conn,
        ) as mock_primary_conn,
        patch.object(
            service,
            "generate_session_id",
            side_effect=lambda chat_id: f"session-{chat_id}",
        ),
    ):
        rows = service.get_all_messages_for_user("user-1", prefer_replica_read=True)

    assert rows == [("user", "fallback")]
    mock_primary_conn.assert_called_once()


@pytest.mark.asyncio
async def test_get_users_to_extract_passes_replica_read_url_to_sync_computation():
    db = AsyncMock()
    chats_result = MagicMock()
    chats_result.fetchall.return_value = [("user-1", "chat-1")]
    log_result = MagicMock()
    log_result.fetchall.return_value = []
    db.execute = AsyncMock(side_effect=[chats_result, log_result])

    with (
        patch.object(
            service,
            "_resolve_sync_read_db_url",
            return_value="postgresql://replica-host:5432/inty",
        ),
        patch.object(service.asyncio, "to_thread", AsyncMock(return_value=["user-1"])) as mock_to_thread,
    ):
        user_ids = await service.get_users_to_extract(db, prefer_replica_read=True)

    assert user_ids == ["user-1"]
    assert mock_to_thread.await_count == 1
    called_args = mock_to_thread.await_args.args
    assert called_args[0] is service._compute_users_to_extract_sync
    assert called_args[-1] == "postgresql://replica-host:5432/inty"
