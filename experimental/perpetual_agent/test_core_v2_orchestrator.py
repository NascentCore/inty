from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from experimental.perpetual_agent.core_v2.adapters.sms_adapter import SmsAdapter
from experimental.perpetual_agent.core_v2.adapters.telegram_adapter import (
    TelegramInboundEnvelope,
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
) -> tuple[
    Orchestrator,
    EventsRepository,
    CursorRepository,
    PlanRepository,
    MemoryRepository,
]:
    db = SQLiteDatabase(str(tmp_path / "core_v2.sqlite3"))
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
        scheduler_default_sms_recipient="+10000000000",
    )
    return orchestrator, events_repo, cursor_repo, plan_repo, memory_repo


def test_process_inbound_duplicate_is_idempotent(tmp_path: Path) -> None:
    sent: list[tuple[str, str]] = []
    orchestrator, events_repo, _cursor_repo, _plan_repo, _memory_repo = (
        _build_orchestrator(
            tmp_path,
            lambda *, chat_id, text: sent.append((chat_id, text)),
        )
    )
    envelope = TelegramInboundEnvelope(
        update_id=101,
        chat_id="chat_1",
        text="hello",
        message_date_unix=1_700_000_000,
    )
    first = orchestrator.process_inbound_telegram(envelope=envelope)
    second = orchestrator.process_inbound_telegram(envelope=envelope)

    assert first.processed is True
    assert second.processed is False
    assert first.should_advance_cursor is True
    assert second.should_advance_cursor is True
    assert sent == [("chat_1", "收到你的消息：hello")]
    assert events_repo.event_exists("telegram_update_101")
    assert events_repo.event_exists("telegram_update_101_reply")


def test_process_inbound_failure_does_not_require_cursor_advance(
    tmp_path: Path,
) -> None:
    def _raising_send(*, chat_id: str, text: str) -> None:
        raise TimeoutError("network timeout")

    orchestrator, events_repo, _cursor_repo, _plan_repo, _memory_repo = (
        _build_orchestrator(
            tmp_path,
            _raising_send,
        )
    )
    envelope = TelegramInboundEnvelope(
        update_id=202,
        chat_id="chat_2",
        text="please fail",
        message_date_unix=None,
    )
    with pytest.raises(TimeoutError):
        orchestrator.process_inbound_telegram(envelope=envelope)

    assert not events_repo.event_exists("telegram_update_202")
    assert not events_repo.event_exists("telegram_update_202_reply")


def test_scheduler_executes_action_only_once(tmp_path: Path) -> None:
    sent: list[tuple[str, str]] = []
    orchestrator, events_repo, _cursor_repo, plan_repo, _memory_repo = (
        _build_orchestrator(
            tmp_path,
            lambda *, chat_id, text: sent.append((chat_id, text)),
        )
    )
    envelope = TelegramInboundEnvelope(
        update_id=303,
        chat_id="chat_3",
        text="prefer telegram",
        message_date_unix=None,
    )
    orchestrator.process_inbound_telegram(envelope=envelope)
    due_actions = plan_repo.list_due_actions(
        now=(datetime.now(timezone.utc) + timedelta(minutes=120)).replace(
            microsecond=0
        ),
        limit=10,
    )
    assert len(due_actions) == 1
    first_count = orchestrator.run_scheduler_once(
        now=due_actions[0].scheduled_at,
    )
    second_count = orchestrator.run_scheduler_once(
        now=due_actions[0].scheduled_at,
    )

    assert first_count == 1
    assert second_count == 0
    assert events_repo.event_exists("telegram_update_303_reply")
    assert events_repo.event_exists(f"action_{due_actions[0].action_id}_result")
    assert sent[-1][0] == "chat-default"


def test_inbound_failure_rolls_back_event_and_plans(tmp_path: Path) -> None:
    def _raising_send(*, chat_id: str, text: str) -> None:
        raise TimeoutError("network timeout")

    orchestrator, events_repo, _cursor_repo, plan_repo, memory_repo = (
        _build_orchestrator(
            tmp_path,
            _raising_send,
        )
    )
    envelope = TelegramInboundEnvelope(
        update_id=404,
        chat_id="chat_4",
        text="prefer telegram and fail",
        message_date_unix=None,
    )
    with pytest.raises(TimeoutError):
        orchestrator.process_inbound_telegram(envelope=envelope)

    assert not events_repo.event_exists("telegram_update_404")
    assert not events_repo.event_exists("telegram_update_404_reply")
    assert (
        plan_repo.list_due_actions(
            now=datetime.now(timezone.utc),
            limit=10,
        )
        == []
    )
    assert (
        memory_repo.list_memories_by_user(user_id="telegram:chat_4", limit=10)
        == []
    )
