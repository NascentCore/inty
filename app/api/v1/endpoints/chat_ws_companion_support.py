"""Companion WebSocket turn helpers shared by ``chat_ws.py`` and inner-tick delivery.

Generated entirely by Cursor agent for decoupling maintenance-mode ``chat.py`` from
``companion_harness``.
"""

from typing import Any, Optional

from fastapi import HTTPException

from app.core.companion_harness.companion.llm_inference_errors import (
    CompanionLLMInferenceBackendError,
)
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
    normalize_websocket_companion_message_id_uuid,
)
from app.services import chat_history_service

__all__ = [
    "CompanionInferenceUpstreamHTTPException",
    "CompanionLLMInferenceBackendError",
    "_companion_ai_meta_from_turn_result",
    "_companion_rejects_multimodal_user_turn",
    "_persist_companion_user_message_for_bg",
    "_require_websocket_companion_message_id_uuid",
]


class CompanionInferenceUpstreamHTTPException(HTTPException):
    """HTTPException with optional fields merged into ``/chat/ws`` error JSON frames."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        ws_extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.ws_extra = ws_extra or {}


def _companion_rejects_multimodal_user_turn(
    last_user_message: ChatMessage,
) -> bool:
    return last_user_message.has_image_content_part()


async def _persist_companion_user_message_for_bg(
    *,
    session_id: str,
    last_user_message: ChatMessage,
    effective_local_id: Optional[str],
    implicit_greeting_turn: bool,
) -> Optional[int]:
    """Write user message into ``chat_history`` for one companion turn.

    Mirrors the success-path branching:
    - ``implicit_greeting_turn`` -> no row written; returns ``None``.
    - ``effective_local_id`` -> row with ``meta_data.localId``.
    - else -> plain row.
    """
    if implicit_greeting_turn:
        return None
    if effective_local_id:
        return await chat_history_service.add_user_message_async(
            session_id,
            last_user_message,
            meta_data=dump_chat_ws_companion_wire_meta(
                ChatWsCompanionWireMessageMetaData(local_id=effective_local_id)
            ),
        )
    return await chat_history_service.add_user_message_async(
        session_id, last_user_message
    )


def _require_websocket_companion_message_id_uuid(
    request: ChatCompletionRequest,
) -> str:
    """WebSocket companion turns require a client ``message_id`` that parses as UUID."""
    try:
        return normalize_websocket_companion_message_id_uuid(request.message_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _companion_ai_meta_from_turn_result(
    companion_turn: CompanionTurnResult,
    *,
    companion_scheduled_reminder: bool | None = None,
    scheduled_task_id: str | None = None,
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
