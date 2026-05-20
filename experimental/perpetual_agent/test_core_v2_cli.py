from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from experimental.perpetual_agent.core_v2 import main as cli_main
from experimental.perpetual_agent.core_v2.contracts import (
    ChannelType,
    EventDirection,
    InteractionEvent,
)
from experimental.perpetual_agent.core_v2.repositories.events_repo import (
    EventsRepository,
)
from experimental.perpetual_agent.core_v2.repositories.sqlite_db import (
    SQLiteDatabase,
)
from experimental.perpetual_agent.core_v2.repositories.sqlite_schema import (
    init_schema,
)
from experimental.perpetual_agent.core_v2.settings import CompanionSettings


def _build_settings(tmp_path: Path) -> CompanionSettings:
    return CompanionSettings(
        database_path=str(tmp_path / "cli.sqlite3"),
        telegram_bot_token="token_for_test",
        scheduler_default_telegram_chat_id="chat-default",
        scheduler_default_sms_recipient="+10000000000",
    )


def test_admin_replay_command_prints_events(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    settings = _build_settings(tmp_path)
    db = SQLiteDatabase(settings.database_path)
    init_schema(db)
    events_repo = EventsRepository(db)
    events_repo.save_event_idempotent(
        InteractionEvent(
            event_id="evt_cli_1",
            user_id="telegram:1",
            channel=ChannelType.TELEGRAM,
            direction=EventDirection.INBOUND,
            content="hello cli",
            timestamp=datetime.now(timezone.utc),
            metadata={},
        )
    )

    monkeypatch.setattr(cli_main, "get_settings", lambda: settings)
    cli_main.app(
        tokens=[
            "admin",
            "replay",
            "--since-minutes",
            "120",
            "--limit",
            "10",
        ],
        result_action="return_value",
    )
    out = capsys.readouterr().out
    assert "evt_cli_1" in out
    assert "hello cli" in out


def test_serve_inbound_requires_single_consumer_lease(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _build_settings(tmp_path)
    db = SQLiteDatabase(settings.database_path)
    init_schema(db)
    from experimental.perpetual_agent.core_v2.repositories.lease_repo import (
        LeaseRepository,
    )

    lease_repo = LeaseRepository(db)
    assert lease_repo.try_acquire_or_renew(
        lease_key=settings.lease_key_telegram_inbound,
        owner_id="existing-owner",
        ttl_seconds=settings.lease_ttl_seconds,
    )

    monkeypatch.setattr(cli_main, "get_settings", lambda: settings)
    with pytest.raises(RuntimeError, match="lease is held"):
        cli_main.app(
            tokens=[
                "serve",
                "inbound",
                "--once",
            ],
            result_action="return_value",
        )


def test_serve_scheduler_once_command_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _build_settings(tmp_path)
    monkeypatch.setattr(cli_main, "get_settings", lambda: settings)
    cli_main.app(
        tokens=[
            "serve",
            "scheduler",
            "--once",
        ],
        result_action="return_value",
    )
