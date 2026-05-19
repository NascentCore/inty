from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from experimental.perpetual_agent.core_v2.adapters.sms_adapter import SmsAdapter
from experimental.perpetual_agent.core_v2.contracts import (
    ActionStatus,
    ChannelType,
    PlanAction,
)
from experimental.perpetual_agent.core_v2.repositories.cursor_repo import (
    CursorRepository,
)
from experimental.perpetual_agent.core_v2.repositories.events_repo import (
    EventsRepository,
)
from experimental.perpetual_agent.core_v2.repositories.memory_repo import (
    MemoryRepository,
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
from experimental.perpetual_agent.core_v2.runtime.orchestrator import (
    Orchestrator,
)


def _build_orchestrator(
    tmp_path: Path,
    telegram_send_func,
) -> tuple[Orchestrator, EventsRepository, PlanRepository, SmsAdapter]:
    db = SQLiteDatabase(str(tmp_path / "core_v2_scheduler.sqlite3"))
    init_schema(db)
    events_repo = EventsRepository(db)
    memory_repo = MemoryRepository(db)
    plan_repo = PlanRepository(db)
    cursor_repo = CursorRepository(db)
    sms_adapter = SmsAdapter.create_default()
    orchestrator = Orchestrator(
        events_repo=events_repo,
        memory_repo=memory_repo,
        plan_repo=plan_repo,
        cursor_repo=cursor_repo,
        sms_adapter=sms_adapter,
        telegram_send_func=telegram_send_func,
        planner_followup_delay_minutes=60,
        quiet_hours_start_hour_local=23,
        quiet_hours_end_hour_local=8,
        scheduler_default_telegram_chat_id="chat-default",
        scheduler_default_sms_recipient="+19999999999",
    )
    return orchestrator, events_repo, plan_repo, sms_adapter


def _build_due_action(
    *, action_id: str, channel: ChannelType, now: datetime
) -> PlanAction:
    return PlanAction(
        action_id=action_id,
        user_id="telegram:chat_1",
        goal="follow_up_checkin",
        scheduled_at=now - timedelta(minutes=1),
        preferred_channel=channel,
        message_strategy="gentle_checkin",
        constraints={},
        status=ActionStatus.PENDING,
        result_event_id=None,
    )


def test_scheduler_dispatches_sms_and_marks_done(tmp_path: Path) -> None:
    orchestrator, events_repo, plan_repo, sms_adapter = _build_orchestrator(
        tmp_path,
        lambda *, chat_id, text: None,
    )
    now = datetime(2026, 3, 24, 13, 0, tzinfo=timezone.utc)
    action = _build_due_action(
        action_id="act_sms_1", channel=ChannelType.SMS, now=now
    )
    plan_repo.save_action_idempotent(action)

    executed = orchestrator.run_scheduler_once(now=now)

    assert executed == 1
    assert len(sms_adapter.sent_messages) == 1
    assert sms_adapter.sent_messages[0]["recipient"] == "+19999999999"
    assert events_repo.event_exists("action_act_sms_1_result")
    assert (
        plan_repo.list_due_actions(now=now + timedelta(minutes=5), limit=10)
        == []
    )


def test_scheduler_marks_failed_when_telegram_chat_id_missing(
    tmp_path: Path,
) -> None:
    db = SQLiteDatabase(
        str(tmp_path / "core_v2_scheduler_missing_chat.sqlite3")
    )
    init_schema(db)
    events_repo = EventsRepository(db)
    memory_repo = MemoryRepository(db)
    plan_repo = PlanRepository(db)
    cursor_repo = CursorRepository(db)
    sms_adapter = SmsAdapter.create_default()
    orchestrator = Orchestrator(
        events_repo=events_repo,
        memory_repo=memory_repo,
        plan_repo=plan_repo,
        cursor_repo=cursor_repo,
        sms_adapter=sms_adapter,
        telegram_send_func=lambda *, chat_id, text: None,
        planner_followup_delay_minutes=60,
        quiet_hours_start_hour_local=23,
        quiet_hours_end_hour_local=8,
        scheduler_default_telegram_chat_id="",
        scheduler_default_sms_recipient="+19999999999",
    )
    now = datetime(2026, 3, 24, 13, 0, tzinfo=timezone.utc)
    action = _build_due_action(
        action_id="act_tg_missing_chat",
        channel=ChannelType.TELEGRAM,
        now=now,
    )
    plan_repo.save_action_idempotent(action)

    with pytest.raises(
        ValueError, match="COMPANION_SCHEDULER_DEFAULT_TELEGRAM_CHAT_ID"
    ):
        orchestrator.run_scheduler_once(now=now)

    assert (
        plan_repo.list_due_actions(now=now + timedelta(minutes=5), limit=10)
        == []
    )
    assert not events_repo.event_exists("action_act_tg_missing_chat_result")
