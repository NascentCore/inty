"""Tests for companion WS turn meta mapping (#3377)."""

from __future__ import annotations

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.schemas.chat_websocket import ChatWsGeneratedImageMeta
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_queue_delivery,
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


def test_companion_ai_meta_from_turn_result_turn_recall() -> None:
    turn = CompanionTurnResult(
        assistant_text="hi",
        turn_recall="用户提到下周见面",
        user_msg_uuid="550e8400-e29b-41d4-a716-446655440000",
        assistant_msg_uuid="33333333-3333-4333-8333-000000000002",
    )
    meta = companion_ai_meta_from_turn_result(
        turn,
        companion_scheduled_reminder=None,
        scheduled_task_id=None,
    )
    assert meta["turn_recall"] == "用户提到下周见面"


def test_companion_ai_meta_from_queue_delivery_tool_background() -> None:
    meta = companion_ai_meta_from_queue_delivery(
        queue_message_id="queue-msg-1",
        tool_background_started=True,
    )
    assert meta["user_msg_uuid"] == "queue-msg-1"
    assert meta["tool_background_started"] is True
    assert meta["source"] == "chat"


def test_companion_ai_meta_from_queue_delivery_generated_image() -> None:
    meta = companion_ai_meta_from_queue_delivery(
        queue_message_id="queue-msg-2",
        tool_background_started=False,
        generated_image=ChatWsGeneratedImageMeta(
            image_url="file:///tmp/z_image_test.jpeg",
            width=1024,
            height=768,
        ),
    )
    assert meta["generated_image"]["image_url"] == "file:///tmp/z_image_test.jpeg"
    assert meta["generated_image"]["width"] == 1024
