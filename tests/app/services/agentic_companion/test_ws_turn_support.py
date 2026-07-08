"""Tests for companion WS turn meta mapping (#3377)."""

from __future__ import annotations

from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
)
from app.core.companion_harness.agentic_companion.types import (
    OutputMessageKind,
    WireAssistantSource,
)
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.schemas.chat_websocket import ChatWsGeneratedImageMeta
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_queue_delivery,
    companion_ai_meta_from_turn_result,
)


def _ready_message(
    *,
    wire_assistant_source: WireAssistantSource,
    tool_background_started: bool,
) -> ReadyOutputMessage:
    return ReadyOutputMessage(
        message_id="out-1",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="hi",
        sequence=1,
        message_ids=("queue-msg-1",),
        tool_background_started=tool_background_started,
        trace_id="trace-1",
        langsmith_trace_id="ls-trace",
        langsmith_run_id="ls-run",
        turn_recall="brief",
        wire_assistant_source=wire_assistant_source,
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
        message=_ready_message(
            wire_assistant_source=WireAssistantSource.CHAT,
            tool_background_started=True,
        ),
        queue_message_id="queue-msg-1",
    )
    assert meta["user_msg_uuid"] == "queue-msg-1"
    assert meta["tool_background_started"] is True
    assert meta["source"] == "chat"
    assert meta["langsmith_trace_id"] == "ls-trace"
    assert meta["turn_recall"] == "brief"


def test_companion_ai_meta_from_queue_delivery_greeting_source() -> None:
    meta = companion_ai_meta_from_queue_delivery(
        message=_ready_message(
            wire_assistant_source=WireAssistantSource.GREETING,
            tool_background_started=False,
        ),
        queue_message_id="queue-msg-1",
    )
    assert meta["source"] == "greeting"


def test_companion_ai_meta_from_queue_delivery_generated_image() -> None:
    meta = companion_ai_meta_from_queue_delivery(
        message=_ready_message(
            wire_assistant_source=WireAssistantSource.CHAT,
            tool_background_started=False,
        ),
        queue_message_id="queue-msg-2",
        generated_image=ChatWsGeneratedImageMeta(
            image_url="file:///tmp/z_image_test.jpeg",
            width=1024,
            height=768,
        ),
    )
    assert (
        meta["generated_image"]["image_url"] == "file:///tmp/z_image_test.jpeg"
    )
    assert meta["generated_image"]["width"] == 1024
