import importlib
import sys
import types
from unittest.mock import AsyncMock, patch

import pytest


def _load_push_scheduler_service_module():
    fake_config = types.SimpleNamespace(
        push_notification=types.SimpleNamespace(
            enabled=True, festival_memory_enabled=False, batch_size=128
        ),
        memory_extraction=types.SimpleNamespace(enabled=True, cron_hour=3),
        user_analytics_report=types.SimpleNamespace(enabled=False),
    )
    fake_core_config_module = types.ModuleType("app.core.config")
    fake_core_config_module.global_config_loaded_from_config_yaml = fake_config

    fake_db_session_module = types.ModuleType("app.db.session")
    fake_db_session_module.AsyncSessionLocal = lambda: None
    fake_db_session_module.AsyncSessionLocalReplica = None

    fake_models_memory_module = types.ModuleType("app.models.memory")
    fake_models_memory_module.FestivalMemoryConfig = type("FestivalMemoryConfig", (), {})

    fake_festival_memory_module = types.ModuleType("app.services.festival_memory_service")
    fake_festival_memory_module.DEFAULT_MIN_ROUNDS_IN_WINDOW = 3

    fake_memory_extraction_module = types.ModuleType(
        "app.services.memory_extraction_service"
    )

    async def _dummy_extract(*args, **kwargs):
        return None

    async def _dummy_get_users(*args, **kwargs):
        return []

    fake_memory_extraction_module.extract_and_save = _dummy_extract
    fake_memory_extraction_module.get_users_to_extract = _dummy_get_users

    fake_push_notification_module = types.ModuleType(
        "app.services.push_notification_service"
    )

    async def _dummy_process(*args, **kwargs):
        return (0, 0)

    async def _dummy_discover(*args, **kwargs):
        return 0

    async def _dummy_init(*args, **kwargs):
        return None

    fake_push_notification_module.discover_new_users_for_push = _dummy_discover
    fake_push_notification_module.discover_users_with_updated_tokens = _dummy_discover
    fake_push_notification_module.initialize_push_system = _dummy_init
    fake_push_notification_module.process_festival_memory_push_batch = _dummy_process
    fake_push_notification_module.process_push_batch = _dummy_process

    fake_analytics_report_module = types.ModuleType(
        "app.services.user_analytics_report_service"
    )

    async def _dummy_report(*args, **kwargs):
        return None

    fake_analytics_report_module.compute_and_save_daily_report = _dummy_report
    fake_analytics_report_module.compute_and_save_weekly_report = _dummy_report

    sys.modules.pop("app.services.push_scheduler_service", None)
    with patch.dict(
        sys.modules,
        {
            "app.core.config": fake_core_config_module,
            "app.db.session": fake_db_session_module,
            "app.models.memory": fake_models_memory_module,
            "app.services.festival_memory_service": fake_festival_memory_module,
            "app.services.memory_extraction_service": fake_memory_extraction_module,
            "app.services.push_notification_service": fake_push_notification_module,
            "app.services.user_analytics_report_service": fake_analytics_report_module,
        },
    ):
        return importlib.import_module("app.services.push_scheduler_service")


push_scheduler_module = _load_push_scheduler_service_module()
PushSchedulerService = push_scheduler_module.PushSchedulerService


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
        patch.object(
            push_scheduler_module,
            "AsyncSessionLocalReplica",
            _SessionFactory([read_db]),
        ),
        patch.object(
            push_scheduler_module,
            "AsyncSessionLocal",
            _SessionFactory([write_db]),
        ),
        patch.object(push_scheduler_module, "memory_get_users_to_extract", mock_get_users),
        patch.object(push_scheduler_module, "memory_extract_and_save", mock_extract),
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


@pytest.mark.asyncio
async def test_discover_new_users_prefers_replica_session_for_reads():
    replica_db = AsyncMock()
    primary_db = AsyncMock()
    mock_discover = AsyncMock(return_value=5)

    with (
        patch.object(
            push_scheduler_module,
            "AsyncSessionLocalReplica",
            _SessionFactory([replica_db]),
        ),
        patch.object(
            push_scheduler_module,
            "AsyncSessionLocal",
            _SessionFactory([primary_db]),
        ),
        patch.object(push_scheduler_module, "discover_new_users_for_push", mock_discover),
    ):
        scheduler = PushSchedulerService()
        await scheduler._discover_new_users()

    mock_discover.assert_awaited_once_with(replica_db, batch_size=128)


@pytest.mark.asyncio
async def test_discover_updated_tokens_uses_replica_read_and_primary_write():
    replica_db = AsyncMock()
    primary_db = AsyncMock()
    mock_discover = AsyncMock(return_value=3)

    with (
        patch.object(
            push_scheduler_module,
            "AsyncSessionLocalReplica",
            _SessionFactory([replica_db]),
        ),
        patch.object(
            push_scheduler_module,
            "AsyncSessionLocal",
            _SessionFactory([primary_db]),
        ),
        patch.object(
            push_scheduler_module,
            "discover_users_with_updated_tokens",
            mock_discover,
        ),
    ):
        scheduler = PushSchedulerService()
        await scheduler._discover_users_with_updated_tokens()

    mock_discover.assert_awaited_once()
    assert mock_discover.await_args.args[0] is replica_db
    assert mock_discover.await_args.kwargs == {"batch_size": 128, "write_db": primary_db}
