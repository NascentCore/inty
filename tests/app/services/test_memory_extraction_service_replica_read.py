from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import pytest

from app.services import memory_extraction_service as service


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
        patch(
            "app.services.memory_extraction_service.get_chat_history_replica_connection",
            return_value=replica_conn,
        ) as mock_replica_conn,
        patch(
            "app.services.memory_extraction_service.get_chat_history_connection"
        ) as mock_primary_conn,
        patch(
            "app.services.memory_extraction_service.generate_session_id",
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
        patch(
            "app.services.memory_extraction_service.get_chat_history_replica_connection",
            side_effect=psycopg.OperationalError("replica not available"),
        ),
        patch(
            "app.services.memory_extraction_service.get_chat_history_connection",
            return_value=primary_conn,
        ) as mock_primary_conn,
        patch(
            "app.services.memory_extraction_service.generate_session_id",
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
        patch(
            "app.services.memory_extraction_service._resolve_sync_read_db_url",
            return_value="postgresql://replica-host:5432/inty",
        ),
        patch(
            "app.services.memory_extraction_service.asyncio.to_thread",
            new=AsyncMock(return_value=["user-1"]),
        ) as mock_to_thread,
    ):
        user_ids = await service.get_users_to_extract(db, prefer_replica_read=True)

    assert user_ids == ["user-1"]
    assert mock_to_thread.await_count == 1
    called_args = mock_to_thread.await_args.args
    assert called_args[0] is service._compute_users_to_extract_sync
    assert called_args[-1] == "postgresql://replica-host:5432/inty"
