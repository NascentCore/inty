from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from experimental.perpetual_agent.core_v2.contracts import (
    ActionStatus,
    ChannelType,
    EventDirection,
    InteractionEvent,
    PlanAction,
)
from experimental.perpetual_agent.core_v2.repositories.cursor_repo import (
    CursorRepository,
)
from experimental.perpetual_agent.core_v2.repositories.events_repo import (
    EventsRepository,
)
from experimental.perpetual_agent.core_v2.repositories.plan_repo import (
    PlanRepository,
)
from experimental.perpetual_agent.core_v2.repositories.sqlite_db import (
    SQLiteDatabase,
)
from experimental.perpetual_agent.core_v2.repositories.sqlite_schema import (
    init_schema,
)


def _db(tmp_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(str(tmp_path / "core_v2.sqlite3"))
    init_schema(db)
    return db


def test_events_repo_idempotent_insert(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = EventsRepository(db)
    event = InteractionEvent(
        event_id="evt_1",
        user_id="telegram:1",
        channel=ChannelType.TELEGRAM,
        direction=EventDirection.INBOUND,
        content="hello",
        timestamp=datetime(2026, 3, 24, tzinfo=timezone.utc),
        metadata={},
    )
    assert repo.save_event_idempotent(event) is True
    assert repo.save_event_idempotent(event) is False
    assert repo.event_exists("evt_1") is True


def test_cursor_repo_set_get(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = CursorRepository(db)
    assert repo.get_cursor(cursor_key="telegram_last_applied_update_id") is None
    repo.set_cursor(
        cursor_key="telegram_last_applied_update_id",
        cursor_value="101",
    )
    assert (
        repo.get_cursor(cursor_key="telegram_last_applied_update_id") == "101"
    )


def test_plan_repo_due_claim_done_idempotent(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = PlanRepository(db)
    action = PlanAction(
        action_id="act_1",
        user_id="telegram:1",
        goal="follow_up_checkin",
        scheduled_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        preferred_channel=ChannelType.TELEGRAM,
        message_strategy="gentle_checkin",
        constraints={},
        status=ActionStatus.PENDING,
        result_event_id=None,
    )
    assert repo.save_action_idempotent(action) is True
    assert repo.save_action_idempotent(action) is False

    due = repo.list_due_actions(
        now=datetime(2026, 3, 24, tzinfo=timezone.utc),
        limit=10,
    )
    assert len(due) == 1
    assert repo.claim_action_running(action_id="act_1") is True
    assert repo.claim_action_running(action_id="act_1") is False
    assert (
        repo.mark_done(action_id="act_1", result_event_id="evt_result") is True
    )
    assert (
        repo.mark_done(action_id="act_1", result_event_id="evt_result") is False
    )


def test_plan_repo_mark_failed_from_pending(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = PlanRepository(db)
    action = PlanAction(
        action_id="act_failed",
        user_id="telegram:1",
        goal="follow_up_checkin",
        scheduled_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        preferred_channel=ChannelType.TELEGRAM,
        message_strategy="gentle_checkin",
        constraints={},
        status=ActionStatus.PENDING,
        result_event_id=None,
    )
    repo.save_action_idempotent(action)
    assert repo.mark_failed(action_id="act_failed") is True
    assert repo.mark_failed(action_id="act_failed") is False
