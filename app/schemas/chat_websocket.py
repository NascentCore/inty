"""JSON wire protocol for ``/api/v1/chat/ws``.

This package defines Pydantic models for WebSocket text frames (JSON objects) exchanged
between clients and the Inty chat backend. It is the authoritative spec for client
implementations; user-visible ``message`` strings on error paths remain English per
``app/AGENTS.md``. Companion chat ``meta_data`` blobs (user + assistant + ``tool_bg``)
are centralized in :class:`ChatWsCompanionWireMessageMetaData`.

Companion WS downlink completion types (:class:`ChatWsAssistantMessage`,
:class:`ChatWsCompletionData`, :class:`ChatWebSocketQueuedSuccessFrame`) are defined in
Phase 1 only; emit/parse paths still use loose dicts until Phase 2 adoption
(`GitHub issue #3208 <https://github.com/NascentCore/inty/issues/3208>`_).

Direction tags in model docstrings:

- **Client → server**: uplink JSON the client sends.
- **Server → client (immediate)**: JSON sent with ``WebSocket.send_json`` on the same
  connection, not via the per-connection outbound FIFO used for business replies.
- **Server → client (queued)**: JSON delivered through ``outbound_queue`` and
  ``chat_ws_outbound_pump`` (serialized with other assistant/business payloads).

Chat message bodies reuse :class:`app.schemas.chat.ChatCompletionRequest` (shared with HTTP
completions); time fields reuse :class:`app.schemas.chat.UserTimeContext``.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.biz_action import BizAction
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessageContentPart,
    UserTimeContext,
)


def normalize_websocket_companion_message_id_uuid(raw: Optional[str]) -> str:
    """Canonical RFC4122 UUID string for WebSocket companion ``message_id`` / transcript user row."""
    if raw is None or not str(raw).strip():
        raise ValueError("message_id is required and must be a UUID")
    try:
        return str(uuid.UUID(str(raw).strip()))
    except ValueError as exc:
        raise ValueError("message_id must be a valid UUID") from exc


class ChatWsPingFrame(BaseModel):
    """**Client → server** keepalive; resets idle timer (see chat WebSocket handler)."""

    type: Literal["ping"] = "ping"


class ChatWsPongFrame(BaseModel):
    """**Server → client (immediate)** reply to :class:`ChatWsPingFrame`."""

    type: Literal["pong"] = "pong"


class ChatWsClientContextFrame(BaseModel):
    """**Client → server** session time context; merged into later chat frames when omitted."""

    type: Literal["client_context"] = "client_context"
    time_context: UserTimeContext


class ChatWsClientContextAckFrame(BaseModel):
    """**Server → client (immediate)** result of validating ``time_context``."""

    type: Literal["client_context_ack"] = "client_context_ack"
    ok: bool


class ChatWsUserSignedOnFrame(BaseModel):
    """**Client → server** control frame: arms inner-tick coords and schedules greeting turn.

    ``message_id`` (RFC4122 UUID) is required; see
    ``/app/core/companion_harness/companion/implicit_signal_messages.py``.
    """

    type: Literal["user_signed_on"] = "user_signed_on"
    agent_id: str = Field(..., min_length=1)
    message_id: str = Field(
        ...,
        min_length=1,
        description="RFC4122 UUID for log correlation and companion transcript user_msg_uuid.",
    )


class ChatWsUserSignedOutFrame(BaseModel):
    """**Client → server** control frame: records user leaving the chat channel in companion runtime events JSONL."""

    type: Literal["user_signed_out"] = "user_signed_out"
    agent_id: str = Field(..., min_length=1)
    message_id: Optional[str] = Field(
        default=None,
        description="Optional RFC4122 UUID string for client/server log correlation.",
    )


class ChatWsUserSignedOnAckFrame(BaseModel):
    """**Server → client (immediate)** result of ``user_signed_on`` handling.

    Known ``reason`` values include ``not_supported``, ``invalid_payload``, ``missing_message_id``,
    ``invalid_message_id``, ``agent_mismatch``, ``server_error``; the wire may carry other strings
    for forward compatibility. ``proactive_heartbeat_disabled`` is legacy (coords are armed for
    scheduled companion reminders even when proactive and maintenance inner-tick are disabled).
    """

    type: Literal["user_signed_on_ack"] = "user_signed_on_ack"
    ok: bool
    reason: Optional[str] = None


class ChatWsUserSignedOutAckFrame(BaseModel):
    """**Server → client (immediate)** acceptance of ``user_signed_out``.

    When ``ok`` is true, scope teardown (session shutdown, memory delete, history clear) continues
    asynchronously on the server. Known ``reason`` values for ``ok: false`` include
    ``not_supported``, ``invalid_payload``, ``agent_mismatch``, ``server_error``; the wire may carry
    other strings for forward compatibility.
    """

    type: Literal["user_signed_out_ack"] = "user_signed_out_ack"
    ok: bool
    reason: Optional[str] = None


class ChatWsWsConnDroppedFrame(BaseModel):
    """**Client → server** control frame: prior transport disconnect context for companion runtime events JSONL."""

    type: Literal["ws_conn_dropped"] = "ws_conn_dropped"
    agent_id: str = Field(..., min_length=1)
    dropped_at_utc: str = Field(
        ...,
        min_length=1,
        description="ISO8601 UTC timestamp when the client observed the disconnect.",
    )
    message_id: Optional[str] = Field(
        default=None,
        description="Optional RFC4122 UUID string for client/server log correlation.",
    )
    ws_close_code: Optional[int] = Field(
        default=None,
        description="WebSocket close code from the client stack, if available.",
    )
    ws_close_reason: Optional[str] = Field(
        default=None,
        description="WebSocket close reason from the client stack, if available.",
    )


class ChatWsSignificancePerception(BaseModel):
    """``meta_data.significance_perception`` from dual-LLM envelope (partial dicts allowed)."""

    importance_round: Optional[int] = None
    importance_user_message: Optional[int] = None
    importance_assistant_message: Optional[int] = None


class ChatWsGeneratedImageMeta(BaseModel):
    """``meta_data.generated_image`` on tool_bg downlink frames."""

    image_url: str = Field(min_length=1)
    width: int = 0
    height: int = 0


class ChatWsWsConnDroppedAckFrame(BaseModel):
    """**Server → client (immediate)** result of ``ws_conn_dropped`` handling.

    Known ``reason`` values include ``not_supported``, ``invalid_payload``, ``agent_mismatch``,
    ``server_error``; the wire may carry other strings for forward compatibility.
    """

    type: Literal["ws_conn_dropped_ack"] = "ws_conn_dropped_ack"
    ok: bool
    reason: Optional[str] = None


class ChatWsCompanionWireMessageMetaData(BaseModel):
    """Single schema for ``meta_data`` on companion ``/api/v1/chat/ws`` chat_history rows and downlink bodies.

    **Client → server** (persisted on user rows): optimistic ``localId`` via :attr:`local_id`.
    **Server → client** (assistant ``choices[].message`` and ``tool_bg`` payloads): correlation,
    modality, inner-tick, LangSmith, tool-background flags, etc. The same type is used for any
    chat WebSocket user row that only carries ``localId`` (e.g. subscription-limit path). Keys not
    listed remain valid via ``extra="allow"`` (legacy DB rows, analytics-only keys, future product fields).

    Do not use bool value to specify type.
    Must use message_type enum to specify type.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    local_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("localId", "local_id"),
        serialization_alias="localId",
        description="Client optimistic id; stored under ``localId`` on wire / DB JSON.",
    )
    inner_tick: Optional[bool] = None
    # TODO: remove validation_alias for heartbeat; no backward compat needed
    proactive_chat: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("proactive_chat", "heartbeat"),
    )
    # TODO: remove validation_alias for companion_proactive_heartbeat; no backward compat needed
    companion_proactive_chat: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices(
            "companion_proactive_chat", "companion_proactive_heartbeat"
        ),
    )
    # TODO(#3400): Rename wire field when ``INNER_TICK_MONOLOG`` track lands (keep alias for compat).
    companion_maintenance_inner_tick: Optional[bool] = None
    companion_scheduled_reminder: Optional[bool] = None
    scheduled_task_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("scheduledTaskId", "scheduled_task_id"),
        serialization_alias="scheduledTaskId",
        description="Companion schedule_queue task id when this turn fires a due reminder.",
    )

    source: Optional[str] = None
    bootstrap_round_index: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "bootstrapRoundIndex", "bootstrap_round_index"
        ),
        serialization_alias="bootstrapRoundIndex",
        description="1-based LLM round index within USER_CHAT_BOOTSTRAP sync tool loop.",
    )
    inner_tick_activity: Optional[str] = None
    trace_id: Optional[str] = None
    user_msg_uuid: Optional[str] = None
    assistant_msg_uuid: Optional[str] = None
    reply_to_user_msg_uuid: Optional[str] = None
    langsmith_trace_id: Optional[str] = None
    langsmith_run_id: Optional[str] = None
    significance_perception: Optional[ChatWsSignificancePerception] = None
    turn_recall: Optional[str] = Field(
        default=None,
        description=(
            "Ephemeral Turn Brief from dual-LLM envelope; Phase A plumbing (#3342)."
        ),
    )
    tool_background_started: Optional[bool] = None
    context_mode: Optional[str] = None
    tool_bg_output_to_user: Optional[bool] = None
    tool_bg_generation_deliver: Optional[bool] = None
    generated_image: Optional[ChatWsGeneratedImageMeta] = None
    tool_bg_local_image_paths: Optional[list[str]] = None
    transcript_compaction: Optional[dict[str, Any]] = None

    # TODO(refactoring): Define a enum for message_type, and remove all of the bool members
    # that represent message_type, like inner_tick, proactive_chat, companion_proactive_chat, etc.
    message_type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("messageType", "message_type"),
        serialization_alias="messageType",
    )
    agent_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("agentId", "agent_id"),
        serialization_alias="agentId",
    )
    phone_call: Optional[dict[str, Any]] = None
    premium_only: Optional[bool] = None

    audio_duration: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("audioDuration", "audio_duration"),
        serialization_alias="audioDuration",
    )


def dump_chat_ws_companion_wire_meta(
    meta: ChatWsCompanionWireMessageMetaData,
) -> dict[str, Any]:
    """Serialize companion WebSocket ``meta_data`` for ORM / ``send_json`` (omit nulls, camelCase aliases)."""
    return meta.model_dump(exclude_none=True, by_alias=True)


class ChatWsPersistedAssistantRow(BaseModel):
    """Mirror of ``chat_history_service.get_ai_message_info_by_id`` for Phase 2 builder input."""

    id: int
    content: str
    audio_url: Optional[str] = None
    meta_data: Optional[dict[str, Any]] = None
    timestamp: Optional[str] = None


class ChatWsAssistantMessage(BaseModel):
    """**Server → client (queued)** assistant row inside ``choices[].message`` (companion WS)."""

    model_config = ConfigDict(populate_by_name=True)

    role: Literal["assistant"] = "assistant"
    content: str
    id: Optional[int] = None
    meta_data: Optional[ChatWsCompanionWireMessageMetaData] = None
    timestamp: Optional[str] = None
    audio_url: Optional[str] = None
    content_parts: Optional[list[ChatMessageContentPart]] = None


class ChatWsCompletionChoice(BaseModel):
    """**Server → client (queued)** single OpenAI-shaped choice on companion WS downlink."""

    index: int
    message: ChatWsAssistantMessage
    finish_reason: Literal["stop"] = "stop"


class ChatWsCompletionUsage(BaseModel):
    """Client-contract token counts on companion WS completion ``data`` (not provider semantics)."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatWsCompletionData(BaseModel):
    """**Server → client (queued)** success ``data`` body for companion WS completion frames."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    user_message_id: Optional[int] = None
    business_actions: list[BizAction]
    choices: list[ChatWsCompletionChoice]
    usage: ChatWsCompletionUsage
    local_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("localId", "local_id"),
        serialization_alias="localId",
    )
    source_imate_id: Optional[str] = None


class ChatWebSocketQueuedSuccessFrame(BaseModel):
    """**Server → client (queued)** successful companion chat completion envelope."""

    code: Literal[200] = 200
    message: str = "success"
    data: ChatWsCompletionData
    agent_id: str
    status_line: Optional[str] = None


class ChatWebSocketRequest(BaseModel):
    """**Client → server** chat turn: ``agent_id`` plus embedded HTTP-shaped completion request."""

    agent_id: str
    request: ChatCompletionRequest


class ChatWebSocketQueuedPlainError(BaseModel):
    """**Server → client (queued)** minimal error row: ``code``, ``message``, ``data``, ``agent_id``."""

    code: int
    message: str
    data: Any = None
    agent_id: str


class ChatWebSocketResponse(BaseModel):
    """**Server → client (queued)** business or error envelope (FIFO with assistant JSON).

    Successful completion-shaped frames include OpenAI-style top-level keys (``id``, ``object``,
    ``choices``, ``usage``, …) in addition to ``code`` / ``message`` / ``data`` / ``agent_id``;
    those extras are accepted when validating inbound copies and preserved in dumps via
    ``extra="allow"``. Optional ``status_line`` may appear on successful turns. Error frames may
    include ``error_kind`` and ``llm_provider_http_status`` (and other keys merged from
    ``CompanionInferenceUpstreamHTTPException.ws_extra`` in the handler).

    TODO(issue#3208): type ``data`` as ``ChatWsCompletionData | None``; success
    frames should validate as :class:`ChatWebSocketQueuedSuccessFrame`.
    """

    model_config = ConfigDict(extra="allow")

    code: int = 200
    message: str = "success"
    data: Any = None
    agent_id: str
    status_line: Optional[str] = None
    error_kind: Optional[str] = None
    llm_provider_http_status: Optional[int] = None


def chat_ws_queued_error_dict(
    *,
    status_code: int,
    message: str,
    agent_id: str,
    ws_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a **Server → client (queued)** error dict (optional ``ws_extra`` merged at top level)."""
    payload: dict[str, Any] = {
        "code": status_code,
        "message": message,
        "data": None,
        "agent_id": agent_id,
    }
    if ws_extra:
        payload.update(ws_extra)
    return payload
