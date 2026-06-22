import importlib
import sys
import types
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest


def _load_push_scheduler_service_module():
    fake_config = types.SimpleNamespace(
        push_notification=types.SimpleNamespace(
            enabled=True, festival_memory_enabled=False
        ),
    )
    fake_core_config_module = types.ModuleType("app.core.config")
    fake_core_config_module.global_config_loaded_from_config_yaml = fake_config

    fake_db_session_module = types.ModuleType("app.db.session")
    fake_db_session_module.AsyncSessionLocal = lambda: None
    fake_db_session_module.AsyncSessionLocalReplica = None

    fake_models_memory_module = types.ModuleType("app.models.memory")
    fake_models_memory_module.FestivalMemoryConfig = type(
        "FestivalMemoryConfig", (), {}
    )

    fake_festival_memory_module = types.ModuleType(
        "app.services.festival_memory_service"
    )
    fake_festival_memory_module.DEFAULT_MIN_ROUNDS_IN_WINDOW = 3

    def _dummy_get_pairs(*args, **kwargs):
        return []

    async def _dummy_extract_festival(*args, **kwargs):
        return True

    def _dummy_resolve_sync_read_db_url(*args, **kwargs):
        return "postgresql://primary-host:5432/inty"

    fake_festival_memory_module.get_pairs_with_min_rounds_in_window_sync = (
        _dummy_get_pairs
    )
    fake_festival_memory_module.extract_festival_and_save = (
        _dummy_extract_festival
    )
    fake_festival_memory_module.resolve_sync_read_db_url = (
        _dummy_resolve_sync_read_db_url
    )

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
    fake_push_notification_module.discover_users_with_updated_tokens = (
        _dummy_discover
    )
    fake_push_notification_module.initialize_push_system = _dummy_init
    fake_push_notification_module.process_festival_memory_push_batch = (
        _dummy_process
    )
    fake_push_notification_module.process_push_batch = _dummy_process

    sys.modules.pop("app.services.push_scheduler_service", None)
    with patch.dict(
        sys.modules,
        {
            "app.core.config": fake_core_config_module,
            "app.db.session": fake_db_session_module,
            "app.models.memory": fake_models_memory_module,
            "app.services.festival_memory_service": fake_festival_memory_module,
            "app.services.push_notification_service": fake_push_notification_module,
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


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows=None, rowcount=0):
        self._rows = rows or []
        self.rowcount = rowcount

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeColumn:
    def is_(self, *_args, **_kwargs):
        return True

    def isnot(self, *_args, **_kwargs):
        return True

    def __lt__(self, _other):
        return True

    def __eq__(self, _other):
        return True


class _FakeFestivalMemoryConfig:
    enabled = _FakeColumn()
    run_at_date = _FakeColumn()
    run_at_hour = _FakeColumn()
    id = _FakeColumn()
    last_run_at = _FakeColumn()


class _DummyQuery:
    def where(self, *_args, **_kwargs):
        return self

    def values(self, **_kwargs):
        return self


class _FakeScheduler:
    def __init__(self):
        self.started = False
        self.add_job_calls = []

    def start(self):
        self.started = True

    def add_job(self, *args, **kwargs):
        self.add_job_calls.append((args, kwargs))

    def get_jobs(self):
        return []


def _close_coro_task(coro):
    coro.close()
    return None


@pytest.mark.asyncio
async def test_run_festival_memory_extraction_uses_replica_read_url_and_replica_history_read():
    read_db = AsyncMock()
    claim_db = AsyncMock()
    write_db = AsyncMock()
    config = types.SimpleNamespace(
        id=7,
        timezone="UTC",
        run_at_date=date(2000, 1, 1),
        run_at_hour=0,
        last_run_at=None,
        festival_name="Valentine",
        festival_date=date(2000, 1, 1),
        prompt="extract",
        min_rounds_in_window=5,
        llm_config=None,
    )
    read_db.execute = AsyncMock(return_value=_FakeExecuteResult(rows=[config]))
    claim_db.execute = AsyncMock(return_value=_FakeExecuteResult(rowcount=1))
    claim_db.commit = AsyncMock()
    write_db.rollback = AsyncMock()
    mock_to_thread = AsyncMock(return_value=[("user-1", "agent-1")])
    mock_extract = AsyncMock(return_value=True)

    with (
        patch.object(
            push_scheduler_module,
            "AsyncSessionLocalReplica",
            _SessionFactory([read_db]),
        ),
        patch.object(
            push_scheduler_module,
            "AsyncSessionLocal",
            _SessionFactory([claim_db, write_db]),
        ),
        patch.object(
            push_scheduler_module.festival_memory_service,
            "resolve_sync_read_db_url",
            return_value="postgresql://replica-host:5432/inty",
        ) as mock_resolve_read_url,
        patch.object(
            push_scheduler_module.festival_memory_service,
            "extract_festival_and_save",
            mock_extract,
        ),
        patch.object(
            push_scheduler_module.asyncio, "to_thread", mock_to_thread
        ),
        patch.object(
            push_scheduler_module, "select", return_value=_DummyQuery()
        ),
        patch.object(
            push_scheduler_module, "update", return_value=_DummyQuery()
        ),
        patch.object(push_scheduler_module, "or_", return_value=True),
        patch.object(
            push_scheduler_module,
            "FestivalMemoryConfig",
            _FakeFestivalMemoryConfig,
        ),
    ):
        scheduler = PushSchedulerService()
        await scheduler._run_festival_memory_extraction()

    mock_resolve_read_url.assert_called_once_with(prefer_replica_read=True)
    assert mock_to_thread.await_count == 1
    to_thread_args = mock_to_thread.await_args.args
    assert (
        to_thread_args[0]
        is push_scheduler_module.festival_memory_service.get_pairs_with_min_rounds_in_window_sync
    )
    assert to_thread_args[2] == "postgresql://replica-host:5432/inty"
    assert mock_extract.await_count == 1
    assert mock_extract.await_args.args[0] is write_db
    assert mock_extract.await_args.kwargs["prefer_replica_read"] is True


def test_start_registers_festival_memory_extraction_without_memory_extraction_cron():
    fake_scheduler = _FakeScheduler()
    with (
        patch.object(
            push_scheduler_module,
            "AsyncIOScheduler",
            return_value=fake_scheduler,
        ),
        patch.object(
            push_scheduler_module.asyncio, "create_task", _close_coro_task
        ),
    ):
        scheduler = PushSchedulerService()
        scheduler.start()

    assert fake_scheduler.started is True
    job_ids = {kwargs.get("id") for _args, kwargs in fake_scheduler.add_job_calls}
    assert "run_festival_memory_extraction" in job_ids
    assert "run_memory_extraction" not in job_ids
    assert "run_user_analytics_daily_report" not in job_ids
