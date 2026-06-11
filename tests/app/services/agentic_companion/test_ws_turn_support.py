"""Tests for companion WS turn meta mapping (#3255)."""

from __future__ import annotations

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_turn_result,
)


def test_companion_ai_meta_from_turn_result_scheduled_reminder_fields() -> None:
    turn = CompanionTurnResult(
        assistant_text="reminder",
        assistant_source="inner_tick",
        trace_id="trace-1",
        user_msg_uuid="550e8400-e29b-41d4-a716-446655440000",
        assistant_msg_uuid="33333333-3333-4333-8333-000000000002",
    )
    meta = companion_ai_meta_from_turn_result(
        turn,
        companion_scheduled_reminder=True,
        scheduled_task_id="task-99",
    )
    assert meta["source"] == "inner_tick"
    assert meta["companion_scheduled_reminder"] is True
    assert meta["scheduledTaskId"] == "task-99"
