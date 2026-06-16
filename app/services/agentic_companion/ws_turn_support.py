"""Companion WebSocket turn metadata and harness turn → wire mapping (#3377)."""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.tools.image_gate import (
    generated_image_meta_from_index_slice,
    list_image_asset_records,
)
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    ChatWsGeneratedImageMeta,
    dump_chat_ws_companion_wire_meta,
)
from app.services.agentic_channel.turn import ensure_memory_store_session


def image_asset_baseline_for_scope_store(store) -> int:
    """Index length before a turn; new assets append after this offset."""
    return len(list_image_asset_records(store))


async def generated_image_meta_for_queue_delivery(
    scope: AgentScope,
    *,
    image_asset_baseline: int,
) -> ChatWsGeneratedImageMeta | None:
    """``meta_data.generated_image`` for in-turn sync tools (e.g. ``generate_image``)."""
    session = await ensure_memory_store_session(scope)
    raw = generated_image_meta_from_index_slice(
        session.store,
        image_asset_baseline,
    )
    if raw is None:
        return None
    return ChatWsGeneratedImageMeta.model_validate(raw)


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
        turn_recall=companion_turn.turn_recall or None,
        tool_background_started=(
            True if companion_turn.tool_background_started else None
        ),
        context_mode=companion_turn.turn_start_context_mode or None,
        transcript_compaction=companion_turn.transcript_compaction,
        companion_scheduled_reminder=companion_scheduled_reminder,
        scheduled_task_id=scheduled_task_id,
    )
    return dump_chat_ws_companion_wire_meta(meta)


def companion_ai_meta_from_queue_delivery(
    *,
    queue_message_id: str,
    tool_background_started: bool,
    generated_image: ChatWsGeneratedImageMeta | None = None,
) -> dict[str, Any]:
    """Build assistant ``meta_data`` for queue-delivered App WS user-chat replies."""
    assert queue_message_id != ""
    meta = ChatWsCompanionWireMessageMetaData(
        source="chat",
        user_msg_uuid=queue_message_id,
        tool_background_started=True if tool_background_started else None,
        generated_image=generated_image,
    )
    return dump_chat_ws_companion_wire_meta(meta)
