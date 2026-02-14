from unittest.mock import AsyncMock, patch

import pytest

from app.services.push_scheduler_service import PushSchedulerService


class _SessionContextManager:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionFactory:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def __call__(self):
        return _SessionContextManager(self._sessions.pop(0))


@pytest.mark.asyncio
async def test_run_memory_extraction_uses_replica_for_read_and_primary_for_write():
    read_db = AsyncMock()
    write_db = AsyncMock()
    mock_get_users = AsyncMock(return_value=["u1", "u2"])
    mock_extract = AsyncMock()

    with (
        patch(
            "app.services.push_scheduler_service.AsyncSessionLocalReplica",
            _SessionFactory([read_db]),
        ),
        patch(
            "app.services.push_scheduler_service.AsyncSessionLocal",
            _SessionFactory([write_db]),
        ),
        patch(
            "app.services.push_scheduler_service.memory_get_users_to_extract",
            mock_get_users,
        ),
        patch(
            "app.services.push_scheduler_service.memory_extract_and_save",
            mock_extract,
        ),
    ):
        scheduler = PushSchedulerService()
        await scheduler._run_memory_extraction()

    mock_get_users.assert_awaited_once()
    assert mock_get_users.await_args.args[0] is read_db
    assert mock_get_users.await_args.kwargs == {"prefer_replica_read": True}
    assert mock_extract.await_count == 2
    assert mock_extract.await_args_list[0].args == (write_db, "u1")
    assert mock_extract.await_args_list[0].kwargs == {"prefer_replica_read": True}
    assert mock_extract.await_args_list[1].args == (write_db, "u2")
    assert mock_extract.await_args_list[1].kwargs == {"prefer_replica_read": True}
