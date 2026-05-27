"""Downlink factories and delivery gating."""

from __future__ import annotations

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.agentic_companion.downlink import (
    DownlinkKind,
    bootstrap_interim_downlink,
    downlink_delivers_user_visible_text,
    maintenance_downlink,
    proactive_downlink,
    scheduled_downlink,
    tool_background_downlink,
    user_reply_downlink,
)


def test_user_reply_downlink_binds_turn() -> None:
    turn = CompanionTurnResult(assistant_text="hi", user_msg_uuid="u1")
    event = user_reply_downlink(turn=turn)
    assert event.kind is DownlinkKind.USER_REPLY
    assert event.turn is turn
    assert event.assistant_text == "hi"
    assert downlink_delivers_user_visible_text(event)


def test_proactive_downlink_carries_transcript_user_text() -> None:
    turn = CompanionTurnResult(assistant_text="ping")
    event = proactive_downlink(turn=turn, transcript_user_text="（心跳）")
    assert event.kind is DownlinkKind.PROACTIVE
    assert event.transcript_user_text == "（心跳）"


def test_scheduled_downlink_requires_task_id() -> None:
    turn = CompanionTurnResult(assistant_text="remind")
    event = scheduled_downlink(
        turn=turn,
        transcript_user_text="due",
        scheduled_task_id="task-1",
    )
    assert event.kind is DownlinkKind.SCHEDULED
    assert event.scheduled_task_id == "task-1"


def test_maintenance_empty_text_not_user_visible() -> None:
    turn = CompanionTurnResult(assistant_text="")
    event = maintenance_downlink(turn=turn, transcript_user_text="（内在节拍）")
    assert not downlink_delivers_user_visible_text(event)


def test_tool_background_respects_output_to_user() -> None:
    hidden = tool_background_downlink(
        tool_output=_tool_event(output_to_user=False, text="secret"),
    )
    assert not downlink_delivers_user_visible_text(hidden)
    visible = tool_background_downlink(
        tool_output=_tool_event(output_to_user=True, text="here"),
    )
    assert downlink_delivers_user_visible_text(visible)


def test_bootstrap_interim_downlink() -> None:
    interim = BootstrapInterimOutput(
        text="round",
        user_msg_uuid="u",
        trace_id="t",
        langsmith_trace_id="",
        langsmith_run_id="",
        round_index=1,
        had_tool_calls=True,
        assistant_msg_uuid="a",
    )
    event = bootstrap_interim_downlink(interim=interim)
    assert event.kind is DownlinkKind.BOOTSTRAP_INTERIM
    assert event.bootstrap_interim is interim


def _tool_event(*, output_to_user: bool, text: str) -> ToolOutputEvent:
    from app.core.companion_harness.companion.scope import CompanionScope
    from app.core.companion_harness.memory.memory_store import MemoryStore

    store = MemoryStore(
        scope=CompanionScope("u", "a", "c"),
        repository=None,
    )
    return ToolOutputEvent(
        scope_registry_key="k",
        memory_store=store,
        user_msg_uuid="u",
        assistant_msg_uuid="a",
        text=text,
        ts="",
        elapsed_ms=0,
        output_to_user=output_to_user,
    )
