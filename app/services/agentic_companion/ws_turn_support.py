"""Companion WebSocket turn metadata and harness turn → wire mapping (#3377)."""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)


def companion_ai_meta_from_turn_result(
    companion_turn: CompanionTurnResult,
    *,
    companion_scheduled_reminder: bool | None,
    scheduled_task_id: str | None,
) -> dict[str, Any]:
    """Build assistant ``meta_data`` for chat_history / WS from one companion kernel turn."""
    sp = companion_turn.significance_perception
    significance = sp if isinstance(sp, dict) and sp else None
    meta = ChatWsCompanionWireMessageMetaData(
        source=companion_turn.assistant_source,
        inner_tick_activity=companion_turn.inner_tick_activity,
        trace_id=companion_turn.trace_id or None,
        user_msg_uuid=companion_turn.user_msg_uuid or None,
        assistant_msg_uuid=companion_turn.assistant_msg_uuid or None,
        langsmith_trace_id=companion_turn.langsmith_trace_id or None,
        langsmith_run_id=companion_turn.langsmith_run_id or None,
        significance_perception=significance,
        tool_background_started=(
            True if companion_turn.tool_background_started else None
        ),
        context_mode=companion_turn.turn_start_context_mode or None,
        transcript_compaction=companion_turn.transcript_compaction,
        companion_scheduled_reminder=companion_scheduled_reminder,
        scheduled_task_id=scheduled_task_id,
    )
    return dump_chat_ws_companion_wire_meta(meta)
