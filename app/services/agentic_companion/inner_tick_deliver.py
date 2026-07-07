"""Persist visible inner-tick turns to chat_history (no channel send)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.models import (
    user_visible_assistant_text,
)
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)
from app.services import chat_history_service
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_turn_result,
)


@dataclass(frozen=True)
class InnerTickVisiblePersistInput:
    """One user-visible inner-tick round after kernel turn completes."""

    session_id: str
    chat_row_agent_id: str
    preset_uid: str
    transcript_user_text: str
    companion_turn: CompanionTurnResult
    user_wire_meta: ChatWsCompanionWireMessageMetaData
    companion_scheduled_reminder: bool | None
    scheduled_task_id: str | None
    log_label: str
    skip_user_history: bool


async def persist_visible_inner_tick_turn(
    persist_input: InnerTickVisiblePersistInput,
) -> bool:
    """Write chat_history rows for a visible inner-tick turn.

    Returns True when non-empty assistant text was persisted.
    Channel delivery is exclusively via AgenticLoop → OutputQueue → pump.
    """
    if not persist_input.skip_user_history:
        user_meta = dump_chat_ws_companion_wire_meta(
            persist_input.user_wire_meta
        )
        await chat_history_service.add_user_message_async(
            persist_input.session_id,
            persist_input.transcript_user_text,
            meta_data=user_meta,
        )

    companion_reply = persist_input.companion_turn.assistant_text
    reply_stripped = user_visible_assistant_text(
        str(companion_reply) if companion_reply is not None else ""
    )
    if reply_stripped is None:
        return False

    companion_ai_meta = companion_ai_meta_from_turn_result(
        persist_input.companion_turn,
        companion_scheduled_reminder=persist_input.companion_scheduled_reminder,
        scheduled_task_id=persist_input.scheduled_task_id,
    )
    await chat_history_service.add_ai_message_sync_async(
        persist_input.session_id,
        companion_reply,
        agent_id=persist_input.chat_row_agent_id,
        meta_data=companion_ai_meta,
    )
    return True
