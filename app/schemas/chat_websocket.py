"""JSON wire protocol for ``/api/v1/chat/ws`` and ``/api/v1/chat/ws/verify``.

This package defines Pydantic models for WebSocket text frames (JSON objects) exchanged
between clients and the Inty chat backend. It is the authoritative spec for client
implementations; user-visible ``message`` strings on error paths remain English per
``app/AGENTS.md``. Companion chat ``meta_data`` blobs (user + assistant + ``tool_bg``)
are centralized in :class:`ChatWsCompanionWireMetaData`.

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

from app.schemas.chat import ChatCompletionRequest, UserTimeContext


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
    """**Client → server** control frame: end companion scope and reset chat history for this chat."""

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
    """**Client → server** control frame: prior transport disconnect context for companion CHAT_LOGS.md."""

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


class ChatWsWsConnDroppedAckFrame(BaseModel):
    """**Server → client (immediate)** result of ``ws_conn_dropped`` handling.

    Known ``reason`` values include ``not_supported``, ``invalid_payload``, ``agent_mismatch``,
    ``server_error``; the wire may carry other strings for forward compatibility.
    """

    type: Literal["ws_conn_dropped_ack"] = "ws_conn_dropped_ack"
    ok: bool
    reason: Optional[str] = None


class ChatWsCompanionWireMetaData(BaseModel):
    """Single schema for ``meta_data`` on companion ``/api/v1/chat/ws`` chat_history rows and downlink bodies.

    **Client → server** (persisted on user rows): optimistic ``localId`` via :attr:`local_id`.
    **Server → client** (assistant ``choices[].message`` and ``tool_bg`` payloads): correlation,
    modality, inner-tick, LangSmith, tool-background flags, etc. The same type is used for any
    chat WebSocket user row that only carries ``localId`` (e.g. subscription-limit path). Keys not
    listed remain valid via ``extra="allow"`` (legacy DB rows, analytics-only keys, future product fields).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    local_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("localId", "local_id"),
        serialization_alias="localId",
        description="Client optimistic id; stored under ``localId`` on wire / DB JSON.",
    )
    inner_tick: Optional[bool] = None
    heartbeat: Optional[bool] = None
    companion_proactive_heartbeat: Optional[bool] = None
    companion_maintenance_inner_tick: Optional[bool] = None
    companion_scheduled_reminder: Optional[bool] = None
    scheduled_task_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("scheduledTaskId", "scheduled_task_id"),
        serialization_alias="scheduledTaskId",
        description="Companion schedule_queue task id when this turn fires a due reminder.",
    )

    source: Optional[str] = None
    inner_tick_activity: Optional[str] = None
    reply_modality: Optional[str] = None
    is_voice: Optional[bool] = None
    voice_message_script: Optional[str] = None
    trace_id: Optional[str] = None
    user_msg_uuid: Optional[str] = None
    assistant_msg_uuid: Optional[str] = None
    reply_to_user_msg_uuid: Optional[str] = None
    langsmith_trace_id: Optional[str] = None
    langsmith_run_id: Optional[str] = None
    significance_perception: Optional[dict[str, Any]] = None
    tool_background_started: Optional[bool] = None
    context_mode: Optional[str] = None
    tool_bg_output_to_user: Optional[bool] = None
    tool_bg_generation_deliver: Optional[bool] = None
    generated_image: Optional[dict[str, Any]] = None
    tool_bg_local_image_paths: Optional[list[str]] = None
    transcript_compaction: Optional[dict[str, Any]] = None

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
    meta: ChatWsCompanionWireMetaData,
) -> dict[str, Any]:
    """Serialize companion WebSocket ``meta_data`` for ORM / ``send_json`` (omit nulls, camelCase aliases)."""
    return meta.model_dump(exclude_none=True, by_alias=True)


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
