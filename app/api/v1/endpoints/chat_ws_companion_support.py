"""Companion WebSocket endpoint helpers (HTTP errors, turn I/O at the wire boundary)."""

from typing import Any, Optional

from fastapi import HTTPException

from app.core.companion_harness.companion.llm_inference_errors import (
    CompanionLLMInferenceBackendError,
)
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
    normalize_websocket_companion_message_id_uuid,
)
from app.services import chat_history_service
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_turn_result as _companion_ai_meta_from_turn_result,
)

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
