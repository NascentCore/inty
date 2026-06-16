"""Companion chat WebSocket: ``/api/v1/chat/ws``.

Only the production companion harness path (companion_harness, technocore, livingsphere).
HTTP chat completions and image/music generation stay in ``chat.py``.
Wire frames: ``app/schemas/chat_websocket.py``; outbound pump: ``app/services/chat_websocket_session.py``.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.tools.image_gate import (
    generated_image_meta_from_index_slice,
)
from app.core.companion_harness.companion.scope_turn_lock import (
    companion_scope_from_foreground_ctx,
    get_scope_turn_lock,
)
from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutputSink,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.core.companion_harness.companion.runtime_events import (
    build_user_signed_out_runtime_event_record,
    build_ws_conn_dropped_runtime_event_record,
)
from app.core.companion_harness.companion.websocket_coordinator import (
    BootstrapInterimDeliverCtx,
    BootstrapInterimQueued,
    ChatWsInflightShutdownRegistry,
    ChatWsInflightTurnTracker,
    CompanionWebSocketCoordinator,
    apply_companion_ws_inner_tick_coords,
)
from app.core.model_selection import select_chat_model
from app.models.user import User
from app.schemas.biz_action import BizAction, ActionType
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
    UserTimeContext,
)
from app.schemas.chat_websocket import (
    ChatWebSocketQueuedPlainError,
    ChatWebSocketRequest,
    ChatWsClientContextAckFrame,
    ChatWsCompanionWireMessageMetaData,
    ChatWsPongFrame,
    ChatWsUserSignedOnAckFrame,
    ChatWsUserSignedOnFrame,
    ChatWsUserSignedOutAckFrame,
    ChatWsUserSignedOutFrame,
    ChatWsWsConnDroppedFrame,
    chat_ws_queued_error_dict,
    dump_chat_ws_companion_wire_meta,
    normalize_websocket_companion_message_id_uuid,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.schemas.response import APIResponse
from app.services import agent_service, chat_history_service, chat_service
from app.services import companion_chat_service
from app.services.chat_websocket_session import chat_ws_outbound_pump
from app.services.ws_session_messages import WsOutboundPayload
from app.services.agentic_companion.downlink import tool_background_downlink
from app.services.agentic_companion.inner_tick_delivery import (
    inner_tick_delivery_for_ws,
)
from app.services.agentic_companion.inner_tick_poll import (
    run_inner_tick_poll,
)
from app.services.agentic_companion.presence_registry import (
    PresenceBusyError,
    companion_presence_registry,
)
from app.services.agentic_companion.session import Session
from app.services.agentic_companion.ws_queue_serving import (
    AppWsQueueDeliveryFlags,
    AppWsUserTurnQueueInput,
    run_app_ws_user_turn_via_queues,
)
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_queue_delivery,
    generated_image_meta_for_queue_delivery,
)
from app.services.agentic_companion.ws_channel_guard import (
    register_app_ws_channel,
    unregister_app_ws_channel,
    ws_reject_reason_if_telegram_active,
)
from app.services.agentic_companion.ws_downlink import WebSocketDownlink
from app.services.phone_call_service import (
    PhoneCallConfigError,
    PhoneCallLimitError,
    phone_call_service,
)
from app.services.chat_service import generate_session_id
from app.services.subscription_service import SubscriptionService
from app.services.voice_service import (
    VoiceService,
    voice_service as default_voice_service,
)
from app.utils.timing import Timer, log_time
from app.schemas.user import User as UserSchema

from app.services.chat_completion_wire import (
    build_companion_ws_completion_data,
    _normalize_chat_response_content,
)
from app.services.agent_status_line import (
    agent_status_line_for_chat_header as _agent_status_line_for_chat_header,
)
from app.api.v1.endpoints.chat_ws_companion_support import (
    CompanionInferenceUpstreamHTTPException,
    CompanionLLMInferenceBackendError,
    _companion_ai_meta_from_turn_result,
    _companion_rejects_multimodal_user_turn,
    _persist_companion_user_message_for_bg,
    _require_websocket_companion_message_id_uuid,
)

from app.api.utils.logger_route import LoggerRoute

router = APIRouter(route_class=LoggerRoute)


def _chat_ws_error_payload_from_http_exception(
    exc: HTTPException, *, agent_id: str
) -> dict[str, Any]:
    detail = exc.detail
    message = detail if isinstance(detail, str) else str(detail)
    ws_extra = getattr(exc, "ws_extra", None)
    return chat_ws_queued_error_dict(
        status_code=exc.status_code,
        message=message,
        agent_id=agent_id,
        ws_extra=ws_extra if isinstance(ws_extra, dict) else None,
    )


# WebSocket: one AsyncSession is bound for the whole connection (Depends(get_async_db)).
# Handlers must not pass that session into asyncio.to_thread or other threads; open a new
# session inside the worker if agentic work runs off the event loop.


def _chat_ws_idle_timeout_seconds() -> float:
    return float(
        global_config_loaded_from_config_yaml.app.features.chat_ws_idle_timeout_seconds
    )


# Starlette ``WebSocket.receive_text`` when ``application_state != CONNECTED`` (race after drop).
_WS_RECEIVE_TEXT_NOT_CONNECTED_MSG: str = (
    'WebSocket is not connected. Need to call "accept" first.'
)


def _is_ws_receive_text_not_connected_runtime_error(exc: BaseException) -> bool:
    return (
        isinstance(exc, RuntimeError)
        and str(exc) == _WS_RECEIVE_TEXT_NOT_CONNECTED_MSG
    )


async def _shutdown_chat_ws_outbound_pump(pump_task: asyncio.Task) -> None:
    """Join ``chat_ws_outbound_pump``; cancel if still running.

    ``WebSocketDisconnect`` after the client has gone is expected during teardown and is logged
    at debug. Other exceptions are logged at error (distinct from normal ``CancelledError``).
    """
    if not pump_task.done():
        pump_task.cancel()
    try:
        await pump_task
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        logger.debug(
            "chat_ws_outbound_pump task ended: client disconnected during pump teardown"
        )
    except Exception:
        logger.exception(
            "chat_ws_outbound_pump failed (e.g. WebSocket send_json); "
            "distinct from normal CancelledError teardown"
        )


def _chat_request_with_merged_ws_time_context(
    request: ChatCompletionRequest,
    ws_session_time_context: Optional[dict],
) -> ChatCompletionRequest:
    """
    单连接上先发送 client_context 时，后续 chat 帧可省略 time_context；
    若请求体已带 user_time_context，以请求为准。
    """
    if not ws_session_time_context:
        return request
    if request.user_time_context is not None:
        return request
    try:
        utc = UserTimeContext.model_validate(ws_session_time_context)
    except ValidationError:
        return request
    return request.model_copy(update={"user_time_context": utc})


async def _enqueue_companion_greeting_ws_turn_after_user_signed_on(
    *,
    db: AsyncSession,
    agent_id: str,
    preset_message_id: str,
    current_user: UserSchema,
    subscription_svc: SubscriptionService,
    voice_svc: VoiceService,
    companion_ws: CompanionWebSocketCoordinator,
    tc_box: list[Optional[dict]],
    outbound_queue: asyncio.Queue[WsOutboundPayload],
) -> None:
    """Run one companion greeting turn scheduled from ``user_signed_on`` (with ``message_id``)."""
    try:
        base = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="")],
            message_id=preset_message_id,
        )
        merged = _chat_request_with_merged_ws_time_context(base, tc_box[0])
        try:
            response = await _agent_chat_ws_completions_impl(
                db=db,
                agent_id=agent_id,
                request=merged,
                current_user=current_user,
                subscription_svc=subscription_svc,
                voice_svc=voice_svc,
                companion_background_sink=companion_ws.background_sink,
                companion_ws_foreground_pending=companion_ws.foreground_pending,
                companion_ws_inner_tick_ctx=companion_ws.inner_tick_context,
                companion_ws=companion_ws,
                implicit_greeting_turn=True,
                ws_outbound_queue=outbound_queue,
            )
        except HTTPException as e:
            await outbound_queue.put(
                _chat_ws_error_payload_from_http_exception(e, agent_id=agent_id)
            )
            return
        if response is None:
            return
        if isinstance(response, dict):
            response_data = dict(response)
        else:
            response_data = response.model_dump(exclude_none=True)
        response_data["agent_id"] = agent_id
        await outbound_queue.put(response_data)
    except asyncio.CancelledError:
        logger.debug(
            "chat_ws user_signed_on greeting cancelled agent_id={}",
            agent_id,
        )
        return
    except Exception:
        logger.exception(
            "chat_ws user_signed_on greeting failed agent_id={}",
            agent_id,
        )


async def _handle_chat_websocket_control_json(
    websocket: WebSocket,
    data: Any,
    tc_box: list[Optional[dict]],
) -> bool:
    """
    Handle ping / client_context on chat WebSockets. tc_box is a length-1 list holding the
    session's last validated time_context dict (or None). Returns True if the frame was consumed.

    **Transport vs logical channel:** control frames (ping/pong, client_context_ack) are answered
    directly on the WebSocket. Proactive chat inner-tick coords are set by ``user_signed_on`` (see
    ``_try_handle_ws_user_signed_on_frame``) and refreshed on each successful WebSocket companion
    chat turn (``_agent_chat_ws_completions_impl``). They are independent of the connection-level outbound queue used
    for assistant/business JSON. Intentionally so: the WebSocket sits *below* the repl/client
    logical session with the agent; control traffic only confirms link/time-context at the wire layer,
    not the agent dialogue FIFO (which is serialized via ``outbound_queue`` + pump).
    """
    if not isinstance(data, dict):
        return False
    msg_type = data.get("type")
    if msg_type == "ping":
        await websocket.send_json(ChatWsPongFrame().model_dump())
        return True
    if msg_type != "client_context":
        return False
    tc_raw = data.get("time_context")
    if not isinstance(tc_raw, dict):
        await websocket.send_json(
            ChatWsClientContextAckFrame(ok=False).model_dump()
        )
        return True
    try:
        validated = UserTimeContext.model_validate(tc_raw)
        dumped = validated.model_dump(exclude_none=True)
        tc_box[0] = dumped if dumped else None
        await websocket.send_json(
            ChatWsClientContextAckFrame(ok=True).model_dump()
        )
    except ValidationError:
        await websocket.send_json(
            ChatWsClientContextAckFrame(ok=False).model_dump()
        )
    return True


async def _try_handle_ws_user_signed_on_frame(
    websocket: WebSocket,
    data: Any,
    *,
    db: AsyncSession,
    current_user: UserSchema,
    companion_ws: CompanionWebSocketCoordinator,
    inflight_turn_tracker: ChatWsInflightTurnTracker,
    ws_conn_id: str,
    ws_leased_agent_id_box: list[Optional[str]],
    outbound_queue: asyncio.Queue[WsOutboundPayload],
    tc_box: list[Optional[dict]],
    subscription_svc: SubscriptionService,
    voice_svc: VoiceService,
    app_version_code: Optional[int],
) -> bool:
    """
    Consume ``{"type":"user_signed_on","agent_id":...}``.

    Product intent: arms inner-tick WebSocket coordinates (proactive chat, maintenance inner-tick,
    and due ``schedule_queue`` reminders share this registration). Requires ``message_id`` (RFC4122);
    missing/invalid ids fail before ack; greeting turn is scheduled before ``user_signed_on_ack``.
    """
    if not isinstance(data, dict) or data.get("type") != "user_signed_on":
        return False
    raw_mid_field = data.get("message_id")
    if raw_mid_field is None or not str(raw_mid_field).strip():
        await websocket.send_json(
            ChatWsUserSignedOnAckFrame(
                ok=False,
                reason="missing_message_id",
            ).model_dump(exclude_none=True)
        )
        return True
    try:
        frame = ChatWsUserSignedOnFrame.model_validate(data)
    except ValidationError:
        await websocket.send_json(
            ChatWsUserSignedOnAckFrame(
                ok=False,
                reason="invalid_payload",
            ).model_dump(exclude_none=True)
        )
        return True
    agent_id = frame.agent_id.strip()
    try:
        preset_mid = normalize_websocket_companion_message_id_uuid(
            frame.message_id
        )
    except ValueError:
        await websocket.send_json(
            ChatWsUserSignedOnAckFrame(
                ok=False,
                reason="invalid_message_id",
            ).model_dump(exclude_none=True)
        )
        return True
    presence_registry = companion_presence_registry()
    prior_leased_agent_id = ws_leased_agent_id_box[0]
    if prior_leased_agent_id is not None and prior_leased_agent_id != agent_id:
        presence_registry.release(
            current_user.id,
            prior_leased_agent_id,
            ws_conn_id,
        )
    try:
        presence_registry.try_register(current_user.id, agent_id, ws_conn_id)
    except PresenceBusyError:
        await websocket.send_json(
            ChatWsUserSignedOnAckFrame(
                ok=False,
                reason="presence_busy",
            ).model_dump(exclude_none=True)
        )
        return True
    ws_leased_agent_id_box[0] = agent_id
    try:
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        if chat.agent_id != agent_id:
            presence_registry.release(current_user.id, agent_id, ws_conn_id)
            ws_leased_agent_id_box[0] = None
            await websocket.send_json(
                ChatWsUserSignedOnAckFrame(
                    ok=False,
                    reason="agent_mismatch",
                ).model_dump(exclude_none=True)
            )
            return True
        agent_scope = AgentScope(
            user_id=str(current_user.id),
            agent_id=agent_id,
        )
        inner_tick_chat_id = agent_scope.memory_store_chat_id()
        companion_ws.store_inner_tick_coords(
            user_id=current_user.id,
            agent_id=agent_id,
            chat_id=inner_tick_chat_id,
        )
        greeting_task = inflight_turn_tracker.spawn(
            _enqueue_companion_greeting_ws_turn_after_user_signed_on(
                db=db,
                agent_id=agent_id,
                preset_message_id=preset_mid,
                current_user=current_user,
                subscription_svc=subscription_svc,
                voice_svc=voice_svc,
                companion_ws=companion_ws,
                tc_box=tc_box,
                outbound_queue=outbound_queue,
            ),
            name=f"chat_ws_user_signed_on_greeting_{ws_conn_id}",
        )
        companion_ws.register_implicit_greeting_turn(greeting_task)
        await websocket.send_json(
            ChatWsUserSignedOnAckFrame(ok=True).model_dump(exclude_none=True)
        )
        logger.info(
            "chat_ws user_signed_on armed inner_tick coords ws_conn_id={} user={} agent={} "
            "chat_id={} received_message_uuid={}",
            ws_conn_id,
            current_user.id,
            agent_id,
            inner_tick_chat_id,
            preset_mid,
        )
    except Exception:
        presence_registry.release(current_user.id, agent_id, ws_conn_id)
        ws_leased_agent_id_box[0] = None
        logger.exception(
            "chat_ws user_signed_on failed ws_conn_id={} agent_id={}",
            ws_conn_id,
            agent_id,
        )
        await websocket.send_json(
            ChatWsUserSignedOnAckFrame(
                ok=False,
                reason="server_error",
            ).model_dump(exclude_none=True)
        )
    return True


async def _try_handle_ws_user_signed_out_frame(
    websocket: WebSocket,
    data: Any,
    *,
    db: AsyncSession,
    current_user: UserSchema,
    companion_ws: CompanionWebSocketCoordinator,
    inflight_turn_tracker: ChatWsInflightTurnTracker,
    subscription_svc: SubscriptionService,
    ws_conn_id: str,
    ws_leased_agent_id_box: list[Optional[str]],
) -> bool:
    """
    Consume ``{"type":"user_signed_out","agent_id":...}``.

    Validates the frame, cancels detached companion turns on this connection, disarms inner-tick
    coords (pauses proactive/maintenance until the next ``user_signed_on``), appends a
    ``user_signed_out`` row to companion ``.companion_runtime_events.jsonl`` (MemoryStore), then
    sends ``user_signed_out_ack``. Does not alter transcript or companion scope persistence.
    """
    if not isinstance(data, dict) or data.get("type") != "user_signed_out":
        return False
    try:
        frame = ChatWsUserSignedOutFrame.model_validate(data)
    except ValidationError:
        await websocket.send_json(
            ChatWsUserSignedOutAckFrame(
                ok=False,
                reason="invalid_payload",
            ).model_dump(exclude_none=True)
        )
        return True
    agent_id = frame.agent_id.strip()
    try:
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        if chat.agent_id != agent_id:
            await websocket.send_json(
                ChatWsUserSignedOutAckFrame(
                    ok=False,
                    reason="agent_mismatch",
                ).model_dump(exclude_none=True)
            )
            return True
        subscription = await subscription_svc.get_user_current_subscription(
            db, current_user.id
        )
        model_override = select_chat_model(
            user=current_user, is_subscribed=bool(subscription)
        )
        recv_msg_uuid = (frame.message_id or "").strip()
        uuid_part = recv_msg_uuid if recv_msg_uuid else "-"
        if ws_leased_agent_id_box[0] == agent_id:
            companion_presence_registry().release(
                current_user.id,
                agent_id,
                ws_conn_id,
            )
            ws_leased_agent_id_box[0] = None
        # TODO(ws-disconnect-lifecycle): #3256 — persist-first; finish turns; mark undelivered.
        await inflight_turn_tracker.cancel_all()
        companion_ws.inner_tick_context.clear()
        companion_chat_service.append_companion_ws_runtime_event(
            user_id=current_user.id,
            agent_id=agent_id,
            chat_id=chat.id,
            resolved_chat_model=model_override,
            record=build_user_signed_out_runtime_event_record(
                user_id=current_user.id,
                agent_id=agent_id,
                chat_id=chat.id,
                received_message_uuid=uuid_part,
            ),
        )
        await websocket.send_json(
            ChatWsUserSignedOutAckFrame(ok=True).model_dump(exclude_none=True)
        )
        logger.info(
            "chat_ws user_signed_out logged companion_runtime_event ws_conn_id={} user={} agent={} chat_id={} "
            "received_message_uuid={}",
            ws_conn_id,
            current_user.id,
            agent_id,
            chat.id,
            recv_msg_uuid or "-",
        )
    except Exception:
        logger.exception(
            "chat_ws user_signed_out failed ws_conn_id={} agent_id={}",
            ws_conn_id,
            agent_id,
        )
        await websocket.send_json(
            ChatWsUserSignedOutAckFrame(
                ok=False,
                reason="server_error",
            ).model_dump(exclude_none=True)
        )
    return True


async def _try_handle_ws_ws_conn_dropped_frame(
    websocket: WebSocket,
    data: Any,
    *,
    db: AsyncSession,
    current_user: UserSchema,
    subscription_svc: SubscriptionService,
    ws_conn_id: str,
) -> bool:
    """
    Consume ``{"type":"ws_conn_dropped","agent_id":...,"dropped_at_utc":...}``.

    Appends a ``ws_conn_dropped`` row to companion ``.companion_runtime_events.jsonl`` (MemoryStore).
    Does not alter inner-tick coords or transcript.
    """
    if not isinstance(data, dict) or data.get("type") != "ws_conn_dropped":
        return False
    try:
        frame = ChatWsWsConnDroppedFrame.model_validate(data)
    except ValidationError:
        await websocket.send_json(
            {
                "type": "ws_conn_dropped_ack",
                "ok": False,
                "reason": "invalid_payload",
            }
        )
        return True
    agent_id = frame.agent_id.strip()
    try:
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        if chat.agent_id != agent_id:
            await websocket.send_json(
                {
                    "type": "ws_conn_dropped_ack",
                    "ok": False,
                    "reason": "agent_mismatch",
                }
            )
            return True
        subscription = await subscription_svc.get_user_current_subscription(
            db, current_user.id
        )
        model_override = select_chat_model(
            user=current_user, is_subscribed=bool(subscription)
        )
        recv_msg_uuid = (frame.message_id or "").strip()
        uuid_part = recv_msg_uuid if recv_msg_uuid else "-"
        code_part = (
            frame.ws_close_code if frame.ws_close_code is not None else "-"
        )
        reason_raw = (frame.ws_close_reason or "").strip()
        reason_part = reason_raw if reason_raw else "-"
        companion_chat_service.append_companion_ws_runtime_event(
            user_id=current_user.id,
            agent_id=agent_id,
            chat_id=chat.id,
            resolved_chat_model=model_override,
            record=build_ws_conn_dropped_runtime_event_record(
                user_id=current_user.id,
                agent_id=agent_id,
                chat_id=chat.id,
                client_dropped_at_utc=frame.dropped_at_utc,
                ws_close_code=code_part,
                ws_close_reason=reason_part,
                received_message_uuid=uuid_part,
            ),
        )
        await websocket.send_json({"type": "ws_conn_dropped_ack", "ok": True})
        logger.info(
            "chat_ws ws_conn_dropped logged companion_runtime_event ws_conn_id={} user={} agent={} chat_id={} "
            "client_dropped_at_utc={} received_message_uuid={}",
            ws_conn_id,
            current_user.id,
            agent_id,
            chat.id,
            frame.dropped_at_utc,
            recv_msg_uuid or "-",
        )
    except Exception:
        logger.exception(
            "chat_ws ws_conn_dropped failed ws_conn_id={} agent_id={}",
            ws_conn_id,
            agent_id,
        )
        await websocket.send_json(
            {
                "type": "ws_conn_dropped_ack",
                "ok": False,
                "reason": "server_error",
            }
        )
    return True


def _resolve_ws_conn_id_from_websocket(websocket: WebSocket) -> str:
    """Prefer client ``ws_conn_id`` query (RFC4122 UUID); else server-generated; invalid query falls back."""
    raw = (websocket.query_params.get("ws_conn_id") or "").strip()
    if not raw:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        generated = str(uuid.uuid4())
        logger.info(
            "chat_ws ws_conn_id_query_invalid using_generated ws_conn_id={} rejected_query={!r}",
            generated,
            raw[:200],
        )
        return generated


async def _get_current_user_from_websocket(
    websocket: WebSocket, db: AsyncSession
) -> Optional[User]:
    auth = websocket.headers.get("authorization")
    token = None
    if auth:
        parts = auth.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
    if token is None or token == "":
        token = websocket.query_params.get("token")
    if token is None or token == "":
        return None
    return await deps.get_user_from_token(token, db)


async def _resolve_assumed_chat_websocket_user(
    *,
    operator: User,
    assume_user_id: Optional[str],
    db: AsyncSession,
) -> UserSchema:
    """
    Evaluation: superuser may pass assume_user_id query (same semantics as live_chat WS).
    Matches HTTP X-Assume-User-Id for chat so eval WebSocket hits the same code path as production /ws.
    """
    operator_schema = UserSchema.model_validate(operator, from_attributes=True)
    if not assume_user_id or not str(assume_user_id).strip():
        return operator_schema
    if not operator.is_superuser:
        logger.warning(
            "chat WebSocket assume_user_id ignored: operator is not superuser "
            f"operator_id={operator.id}"
        )
        return operator_schema
    user_id = str(assume_user_id).strip()
    row = await db.execute(select(User).where(User.id == user_id))
    assumed = row.scalar_one_or_none()
    if assumed is not None and not assumed.deleted_at:
        logger.info(
            "chat WebSocket assuming user: operator={} assumed={}",
            operator.id,
            assumed.id,
        )
        return UserSchema.model_validate(assumed, from_attributes=True)
    logger.warning(
        "chat WebSocket assume_user_id not found or deleted: {}", assume_user_id
    )
    return operator_schema


async def _build_companion_tool_background_ws_payload(
    *,
    db: AsyncSession,
    agent_id: str,
    session_id: str,
    ev: ToolOutputEvent,
    request: ChatCompletionRequest,
    effective_local_id: Optional[str],
    foreground_user_message_id: Optional[int] = None,
) -> WsOutboundPayload:
    # TODO(issue#3208): wrap ``build_companion_ws_completion_data`` in ChatWebSocketQueuedSuccessFrame.
    gi = generated_image_meta_from_index_slice(
        ev.memory_store, ev.image_asset_baseline
    )
    tb_paths: list[str] | None = (
        list(ev.local_image_paths) if ev.local_image_paths else None
    )
    sig = ev.significance_perception if ev.significance_perception else None
    meta_data = dump_chat_ws_companion_wire_meta(
        ChatWsCompanionWireMessageMetaData(
            source="tool_bg",
            trace_id=ev.trace_id or None,
            reply_to_user_msg_uuid=ev.user_msg_uuid or None,
            tool_bg_output_to_user=ev.output_to_user,
            tool_bg_generation_deliver=ev.generation_deliver,
            langsmith_trace_id=ev.langsmith_trace_id or None,
            langsmith_run_id=ev.langsmith_run_id or None,
            generated_image=gi or None,
            tool_bg_local_image_paths=tb_paths,
            significance_perception=sig,
            turn_recall=ev.turn_recall or None,
            inner_tick_activity=ev.inner_tick_activity,
        )
    )
    ai_message_id = await chat_history_service.add_ai_message_sync_async(
        session_id,
        ev.text,
        agent_id=agent_id,
        meta_data=meta_data,
    )
    latest_message_info = None
    try:
        if ai_message_id is not None:
            latest_message_info = (
                await chat_history_service.get_ai_message_info_by_id(
                    db, ai_message_id
                )
            )
    except Exception as e:
        logger.warning(f"tool_bg get_ai_message_info_by_id failed: {e}")
    user_message_id = foreground_user_message_id
    if user_message_id is None:
        try:
            user_message_id = (
                await chat_history_service.get_latest_user_message_id(
                    db, session_id
                )
            )
        except Exception as e:
            logger.warning(f"tool_bg get_latest_user_message_id failed: {e}")
    subscription_actions = [
        BizAction(action_type=ActionType.NONE, message=""),
    ]
    completion = build_companion_ws_completion_data(
        response_text_content=ev.text,
        response_content_parts=None,
        last_user_text="",
        latest_message_info=latest_message_info,
        audio_url=None,
        request=request,
        source_imate_id=request.target_imate_id,
        user_message_id=user_message_id,
        subscription_actions=subscription_actions,
        client_local_id=effective_local_id,
    )
    payload = APIResponse.success(data=completion.model_dump(exclude_none=True))
    out = payload.model_dump(exclude_none=True)
    out["agent_id"] = agent_id
    out["status_line"] = await _agent_status_line_for_chat_header(db, agent_id)
    return out


# TODO(companion-ws-bootstrap-downlink): move materialize into WebSocketDownlink; drop parallel consumer. #3209 #3398
async def _deliver_bootstrap_interim_queued(
    queued: BootstrapInterimQueued,
) -> None:
    """Materialize one bootstrap sync tool-loop round into chat history + WS outbound."""
    ev = queued.ev
    ctx = queued.ctx
    meta_data = dump_chat_ws_companion_wire_meta(
        ChatWsCompanionWireMessageMetaData(
            source="bootstrap_tool_round",
            trace_id=ev.trace_id or None,
            user_msg_uuid=ev.user_msg_uuid or None,
            assistant_msg_uuid=ev.assistant_msg_uuid or None,
            langsmith_trace_id=ev.langsmith_trace_id or None,
            langsmith_run_id=ev.langsmith_run_id or None,
            bootstrap_round_index=ev.round_index,
        )
    )
    ai_message_id = await chat_history_service.add_ai_message_sync_async(
        ctx.session_id,
        ev.text,
        agent_id=ctx.agent_id,
        meta_data=meta_data,
    )
    latest_message_info = None
    try:
        if ai_message_id is not None:
            latest_message_info = (
                await chat_history_service.get_ai_message_info_by_id(
                    ctx.db, ai_message_id
                )
            )
    except Exception as e:
        logger.warning(
            "bootstrap_interim get_ai_message_info_by_id failed: {}", e
        )
    subscription_actions = [
        BizAction(action_type=ActionType.NONE, message=""),
    ]
    completion = build_companion_ws_completion_data(
        response_text_content=ev.text,
        response_content_parts=None,
        last_user_text=ctx.last_user_text,
        latest_message_info=latest_message_info,
        audio_url=None,
        request=ctx.request,
        source_imate_id=ctx.request.target_imate_id,
        user_message_id=None,
        subscription_actions=subscription_actions,
        client_local_id=ctx.effective_local_id,
    )
    payload = APIResponse.success(data=completion.model_dump(exclude_none=True))
    out = payload.model_dump(exclude_none=True)
    out["agent_id"] = ctx.agent_id
    out["status_line"] = await _agent_status_line_for_chat_header(
        ctx.db, ctx.agent_id
    )
    await ctx.outbound_queue.put(out)


async def _companion_ws_bootstrap_interim_consumer(
    companion_ws: CompanionWebSocketCoordinator,
) -> None:
    """Drain ``bootstrap_interim_queued_events`` for the lifetime of one ``/api/v1/chat/ws`` session."""
    while True:
        queued = await companion_ws.bootstrap_interim_queued_events.get()
        try:
            await _deliver_bootstrap_interim_queued(queued)
        except Exception:
            logger.exception("companion_ws bootstrap_interim deliver failed")


@dataclass(frozen=True)
class AppWsQueueDeliveryCtx:
    """Values needed to materialize one queue-delivered App WS completion frame."""

    db: AsyncSession
    user_id: str
    agent_id: str
    chat_id: str
    session_id: str
    request: ChatCompletionRequest
    last_user_message: Any
    last_user_text: str
    effective_local_id: str | None
    companion_preset_uid: str | None
    companion_ws_foreground_pending: dict[str, dict[str, Any]] | None
    outbound_queue: asyncio.Queue[WsOutboundPayload]
    delivery_flags: AppWsQueueDeliveryFlags


async def _deliver_app_ws_user_reply_from_queue(
    ctx: AppWsQueueDeliveryCtx,
    text: str,
) -> None:
    """Persist chat_history and enqueue one WS completion for OutputQueue-delivered text."""
    assert text.strip() != ""
    companion_user_row_id = await _persist_companion_user_message_for_bg(
        session_id=ctx.session_id,
        last_user_message=ctx.last_user_message,
        effective_local_id=ctx.effective_local_id,
        implicit_greeting_turn=False,
    )
    if (
        ctx.companion_preset_uid is not None
        and ctx.companion_ws_foreground_pending is not None
        and ctx.companion_preset_uid in ctx.companion_ws_foreground_pending
    ):
        ctx.companion_ws_foreground_pending[ctx.companion_preset_uid][
            "foreground_user_message_id"
        ] = companion_user_row_id
    assert ctx.delivery_flags.image_asset_baseline_initialized
    generated_image = await generated_image_meta_for_queue_delivery(
        AgentScope(user_id=ctx.user_id, agent_id=ctx.agent_id),
        image_asset_baseline=ctx.delivery_flags.image_asset_baseline,
    )
    companion_ai_meta = companion_ai_meta_from_queue_delivery(
        queue_message_id=ctx.delivery_flags.queue_message_id,
        tool_background_started=ctx.delivery_flags.tool_background_started,
        generated_image=generated_image,
    )
    ai_message_id = await chat_history_service.add_ai_message_sync_async(
        ctx.session_id,
        text,
        agent_id=ctx.agent_id,
        meta_data=companion_ai_meta,
    )
    latest_message_info = None
    try:
        if ai_message_id is not None:
            latest_message_info = (
                await chat_history_service.get_ai_message_info_by_id(
                    ctx.db, ai_message_id
                )
            )
    except Exception as e:
        logger.warning(f"queue deliver get_ai_message_info_by_id failed: {e}")
    user_message_id = companion_user_row_id
    if user_message_id is None:
        try:
            user_message_id = (
                await chat_history_service.get_latest_user_message_id(
                    ctx.db, ctx.session_id
                )
            )
        except Exception as e:
            logger.warning(
                f"queue deliver get_latest_user_message_id failed: {e}"
            )
    response_text_content, response_content_parts = (
        _normalize_chat_response_content(text)
    )
    completion = build_companion_ws_completion_data(
        response_text_content=response_text_content,
        response_content_parts=response_content_parts,
        last_user_text=ctx.last_user_text,
        latest_message_info=latest_message_info,
        audio_url=None,
        request=ctx.request,
        source_imate_id=ctx.request.target_imate_id,
        user_message_id=user_message_id,
        subscription_actions=None,
        client_local_id=ctx.effective_local_id,
    )
    payload = APIResponse.success(data=completion.model_dump(exclude_none=True))
    out = payload.model_dump(exclude_none=True)
    out["agent_id"] = ctx.agent_id
    out["status_line"] = await _agent_status_line_for_chat_header(
        ctx.db, ctx.agent_id
    )
    await ctx.outbound_queue.put(out)


def _alias_ws_foreground_pending_for_queue_message(
    *,
    companion_ws_foreground_pending: dict[str, dict[str, Any]],
    client_message_id: str,
    queue_message_id: str,
) -> None:
    """Map queue message id to the same foreground ctx as the client message id."""
    assert client_message_id != ""
    assert queue_message_id != ""
    ctx = companion_ws_foreground_pending.get(client_message_id)
    if ctx is None:
        return
    companion_ws_foreground_pending[queue_message_id] = ctx


def _clear_ws_foreground_pending_aliases(
    *,
    companion_ws_foreground_pending: dict[str, dict[str, Any]],
    client_message_id: str,
    queue_message_id: str,
) -> None:
    companion_ws_foreground_pending.pop(client_message_id, None)
    if queue_message_id:
        companion_ws_foreground_pending.pop(queue_message_id, None)


async def _agent_chat_ws_completions_impl(
    *,
    db: AsyncSession,
    agent_id: str,
    request: ChatCompletionRequest,
    current_user: UserSchema,
    subscription_svc: SubscriptionService,
    voice_svc: VoiceService = default_voice_service,
    companion_background_sink: Callable[[ToolOutputEvent], None] | None = None,
    companion_ws_foreground_pending: dict[str, dict[str, Any]] | None = None,
    companion_ws_inner_tick_ctx: dict[str, Any] | None = None,
    companion_ws: CompanionWebSocketCoordinator | None = None,
    implicit_greeting_turn: bool = False,
    ws_outbound_queue: asyncio.Queue[WsOutboundPayload] | None = None,
    ws_conn_id: str | None = None,
) -> dict | None:
    """One companion chat turn for ``/api/v1/chat/ws`` (production WebSocket path).

    Companion kernel + wire envelope.
    HTTP-era extras (chat limit gate, legacy TTS, usage accounting, push read side-effects,
    surprise snap, in-frame memory prompts) stay on ``_agent_chat_completions_impl`` or other routes.
    """
    # TODO(cleanup-ws-http-chat-impl): Deduplicate post-turn finalize with HTTP impl where shared.
    # TODO(issue#3208): wrap ``build_companion_ws_completion_data`` in ChatWebSocketQueuedSuccessFrame.
    assert voice_svc is not None
    try:
        request_handling_timer = Timer("请求处理")
        logger.debug(
            f"聊天请求 - agent_id={agent_id}, user_id={current_user.id}, messages={len(request.messages)}"
        )

        with log_time(
            f"获取或创建聊天会话: user_id={current_user.id}, agent_id={agent_id}"
        ):
            chat = await chat_service.get_or_create_chat_by_agent(
                db=db, user_id=current_user.id, agent_id=agent_id
            )

        if chat.agent_id != agent_id:
            logger.error(
                f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: expected={agent_id}, actual={chat.agent_id}",
            )

        agent_scope_inner_tick_chat_id = AgentScope(
            user_id=str(current_user.id),
            agent_id=agent_id,
        ).memory_store_chat_id()

        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")

        last_user_message = user_messages[-1].to_model_content()
        last_user_chat_message = user_messages[-1]
        last_user_text = last_user_chat_message.extract_text_content()
        logger.debug(
            f"聊天请求最后一条用户消息: has_multimodal={isinstance(last_user_message, list)}, text_length={len(last_user_text)}"
        )

        effective_local_id = (
            request.local_id or request.message_id or ""
        ).strip() or None

        implicit_greeting_ws = implicit_greeting_turn
        if (
            implicit_greeting_ws
            and last_user_chat_message.has_image_content_part()
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Implicit greeting turns do not support multimodal or image content"
                ),
            )

        with log_time(f"查询 Agent 数据: {chat.agent_id}"):
            agent_data = await agent_service.get_agent_for_chat(
                db, agent_id=chat.agent_id
            )

        if not agent_data:
            logger.error(f"Agent数据未找到: {chat.agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")

        session_id = generate_session_id(str(chat.id))

        try:
            with log_time(f"获取聊天设置: chat_id={chat.id}"):
                chat_settings = await chat_service.get_or_create_chat_settings(
                    db, chat.id, current_user.id, agent_id
                )

            with log_time(f"AI聊天处理: session_id={session_id}"):
                subscription = (
                    await subscription_svc.get_user_current_subscription(
                        db, current_user.id
                    )
                )
                is_subscribed = bool(subscription)
                model_override = select_chat_model(
                    user=current_user, is_subscribed=is_subscribed
                )
                _agent_cfg = global_config_loaded_from_config_yaml.agent
                _chat_llm_base = (
                    _agent_cfg.chat_llm_base_url or _agent_cfg.base_url or ""
                ).strip() or "https://openrouter.ai/api/v1"
                logger.debug(
                    "chat_turn route=websocket user={} chat_id={} agent_id={} model={} subscribed={} chat_llm_api_base={}",
                    current_user.id,
                    chat.id,
                    agent_id,
                    model_override,
                    is_subscribed,
                    _chat_llm_base,
                )
                # TODO(companion-multimodal-user-turn): After Phase 1, map ``ChatMessage`` content
                # https://github.com/NascentCore/inty/issues/3293
                # parts to ``CompanionUserTurnInput`` and gate on
                # ``chat_model_accepts_image_input(model_override)`` instead of blanket reject.
                if (
                    not implicit_greeting_ws
                    and _companion_rejects_multimodal_user_turn(
                        user_messages[-1]
                    )
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Multimodal user turns with images are not supported for the "
                            "companion kernel on WebSocket yet. Send text-only content."
                        ),
                    )
                phone_call_trigger_number = (
                    None
                    if implicit_greeting_ws
                    else phone_call_service.extract_call_me_at_number(
                        last_user_text
                    )
                )
                if phone_call_trigger_number:
                    try:
                        phone_result = (
                            await phone_call_service.start_outbound_call(
                                db=db,
                                current_user=current_user,
                                agent_id=agent_id,
                                phone_number=phone_call_trigger_number,
                                subscription_svc=subscription_svc,
                                reason="chat_message_call_me_at",
                            )
                        )
                        response_text_content = (
                            "I'm calling you now at "
                            f"{phone_result.to_number_masked}."
                        )
                        response_content_parts = None
                        phone_meta = {
                            "agentId": agent_id,
                            "phone_call": {
                                "trigger": "chat_message_call_me_at",
                                "call_sid": phone_result.call_sid,
                                "status": phone_result.status,
                                "to_number_masked": phone_result.to_number_masked,
                            },
                        }
                    except PhoneCallLimitError as exc:
                        out = dict(exc.error_response)
                        out["agent_id"] = agent_id
                        return out
                    except (PhoneCallConfigError, ValueError) as exc:
                        response_text_content = (
                            "I can't place the phone call yet: " f"{str(exc)}."
                        )
                        response_content_parts = None
                        phone_meta = {
                            "agentId": agent_id,
                            "phone_call": {
                                "trigger": "chat_message_call_me_at",
                                "status": "failed",
                                "reason": str(exc),
                            },
                        }

                    companion_user_row_id = (
                        await _persist_companion_user_message_for_bg(
                            session_id=session_id,
                            last_user_message=last_user_message,
                            effective_local_id=effective_local_id,
                            implicit_greeting_turn=implicit_greeting_ws,
                        )
                    )
                    ai_message_id = await chat_history_service.add_ai_message_sync_async(
                        session_id,
                        response_text_content,
                        agent_id=chat.agent_id,
                        meta_data=dump_chat_ws_companion_wire_meta(
                            ChatWsCompanionWireMessageMetaData.model_validate(
                                phone_meta
                            )
                        ),
                    )
                    if companion_ws_inner_tick_ctx is not None:
                        apply_companion_ws_inner_tick_coords(
                            companion_ws_inner_tick_ctx,
                            user_id=current_user.id,
                            agent_id=agent_id,
                            chat_id=agent_scope_inner_tick_chat_id,
                        )
                    _ = companion_user_row_id
                else:
                    companion_preset_uid: str | None = None
                    if companion_ws_foreground_pending is not None:
                        companion_preset_uid = (
                            _require_websocket_companion_message_id_uuid(
                                request
                            )
                        )
                        companion_ws_foreground_pending[
                            companion_preset_uid
                        ] = {
                            "session_id": session_id,
                            "agent_id": agent_id,
                            "user_id": str(current_user.id),
                            "chat_id": chat.id,
                            "request": request,
                            "effective_local_id": effective_local_id,
                            "chat_voice_id": chat_settings.voice_id,
                            "agent_voice_id": agent_data.get("voice_id"),
                            "agent_gender": agent_data.get("gender"),
                            "agent_settings": agent_data.get("settings"),
                            "language": request.language,
                        }
                    bootstrap_interim_sink: (
                        BootstrapInterimOutputSink | None
                    ) = None
                    if ws_outbound_queue is not None:
                        assert companion_ws is not None
                        # TODO(companion-presence-ws-outbound): deliver via session, not coordinator queue. #3211 #3209 #3398
                        companion_ws.set_bootstrap_interim_deliver_ctx(
                            BootstrapInterimDeliverCtx(
                                db=db,
                                agent_id=agent_id,
                                session_id=session_id,
                                request=request,
                                last_user_text=last_user_text,
                                effective_local_id=effective_local_id,
                                outbound_queue=ws_outbound_queue,
                            )
                        )
                        if implicit_greeting_ws:
                            bootstrap_interim_sink = (
                                companion_ws.bootstrap_interim_output_sink()
                            )
                        _ = bootstrap_interim_sink
                    try:
                        companion_implicit_bundle = ImplicitSignalBundle(
                            client_time=request.user_time_context,
                            user_signed_on=implicit_greeting_ws,
                            server_received_at_utc=datetime.now(timezone.utc),
                        )
                        if implicit_greeting_ws:
                            companion_turn = await companion_chat_service.run_companion_implicit_sign_on_greeting_turn_for_api(
                                user_id=current_user.id,
                                agent_id=agent_id,
                                chat_id=chat.id,
                                user_text=last_user_text,
                                resolved_chat_model=model_override,
                                implicit_signal_bundle=companion_implicit_bundle,
                                session_id=session_id,
                                background_output_sink=companion_background_sink,
                                preset_user_msg_uuid=companion_preset_uid,
                            )
                            if (
                                companion_preset_uid is not None
                                and companion_ws_foreground_pending is not None
                                and not companion_turn.tool_background_started
                            ):
                                companion_ws_foreground_pending.pop(
                                    companion_preset_uid, None
                                )
                        else:
                            assert ws_outbound_queue is not None
                            assert ws_conn_id is not None
                            assert ws_conn_id != ""
                            delivery_flags = AppWsQueueDeliveryFlags()
                            delivery_ctx = AppWsQueueDeliveryCtx(
                                db=db,
                                user_id=str(current_user.id),
                                agent_id=agent_id,
                                chat_id=agent_scope_inner_tick_chat_id,
                                session_id=session_id,
                                request=request,
                                last_user_message=last_user_message,
                                last_user_text=last_user_text,
                                effective_local_id=effective_local_id,
                                companion_preset_uid=companion_preset_uid,
                                companion_ws_foreground_pending=companion_ws_foreground_pending,
                                outbound_queue=ws_outbound_queue,
                                delivery_flags=delivery_flags,
                            )

                            async def send_user_reply(text: str) -> None:
                                await _deliver_app_ws_user_reply_from_queue(
                                    delivery_ctx, text
                                )

                            scope = AgentScope(
                                user_id=str(current_user.id),
                                agent_id=agent_id,
                            )
                            wire_id = f"app:{ws_conn_id}"
                            delivery_result = await run_app_ws_user_turn_via_queues(
                                AppWsUserTurnQueueInput(
                                    scope=scope,
                                    wire_id=wire_id,
                                    user_text=last_user_text,
                                    client_message_id=companion_preset_uid,
                                    implicit_signal_bundle=companion_implicit_bundle,
                                    background_output_sink=companion_background_sink,
                                    delivery_flags=delivery_flags,
                                    send_text=send_user_reply,
                                )
                            )
                            if (
                                companion_preset_uid is not None
                                and companion_ws_foreground_pending is not None
                                and delivery_flags.queue_message_id
                            ):
                                _alias_ws_foreground_pending_for_queue_message(
                                    companion_ws_foreground_pending=companion_ws_foreground_pending,
                                    client_message_id=companion_preset_uid,
                                    queue_message_id=delivery_flags.queue_message_id,
                                )
                            if (
                                companion_preset_uid is not None
                                and companion_ws_foreground_pending is not None
                                and not delivery_result.tool_background_started
                            ):
                                _clear_ws_foreground_pending_aliases(
                                    companion_ws_foreground_pending=companion_ws_foreground_pending,
                                    client_message_id=companion_preset_uid,
                                    queue_message_id=delivery_flags.queue_message_id,
                                )
                            if (
                                not delivery_result.delivered_text.strip()
                                and not delivery_result.tool_background_started
                            ):
                                logger.error(
                                    "Companion queue chat returned no content agent_id={} user_id={}",
                                    agent_id,
                                    current_user.id,
                                )
                                raise HTTPException(
                                    status_code=500,
                                    detail="Chat returned no content",
                                )
                            if companion_ws_inner_tick_ctx is not None:
                                apply_companion_ws_inner_tick_coords(
                                    companion_ws_inner_tick_ctx,
                                    user_id=current_user.id,
                                    agent_id=agent_id,
                                    chat_id=agent_scope_inner_tick_chat_id,
                                )
                            return None
                    except Exception as exc:
                        bg_started_on_exc = bool(
                            getattr(
                                exc, "companion_tool_background_started", False
                            )
                        )
                        if (
                            companion_preset_uid is not None
                            and companion_ws_foreground_pending is not None
                            and not bg_started_on_exc
                        ):
                            _clear_ws_foreground_pending_aliases(
                                companion_ws_foreground_pending=companion_ws_foreground_pending,
                                client_message_id=companion_preset_uid,
                                queue_message_id="",
                            )
                        if bg_started_on_exc:
                            try:
                                bg_user_row_id = await _persist_companion_user_message_for_bg(
                                    session_id=session_id,
                                    last_user_message=last_user_message,
                                    effective_local_id=effective_local_id,
                                    implicit_greeting_turn=implicit_greeting_ws,
                                )
                            except Exception as persist_exc:
                                logger.warning(
                                    "companion bg-survives-fg-fail user message persist failed: {}",
                                    persist_exc,
                                )
                                bg_user_row_id = None
                            if (
                                companion_preset_uid is not None
                                and companion_ws_foreground_pending is not None
                                and companion_preset_uid
                                in companion_ws_foreground_pending
                            ):
                                companion_ws_foreground_pending[
                                    companion_preset_uid
                                ]["foreground_user_message_id"] = bg_user_row_id
                        raise
                    finally:
                        if companion_ws is not None:
                            companion_ws.clear_bootstrap_interim_deliver_ctx()
                    if implicit_greeting_ws:
                        companion_reply = companion_turn.assistant_text
                        companion_ai_meta = _companion_ai_meta_from_turn_result(
                            companion_turn,
                            companion_scheduled_reminder=None,
                            scheduled_task_id=None,
                        )
                        companion_user_row_id = (
                            await _persist_companion_user_message_for_bg(
                                session_id=session_id,
                                last_user_message=last_user_message,
                                effective_local_id=effective_local_id,
                                implicit_greeting_turn=implicit_greeting_ws,
                            )
                        )
                        if (
                            companion_preset_uid is not None
                            and companion_ws_foreground_pending is not None
                            and companion_preset_uid
                            in companion_ws_foreground_pending
                        ):
                            companion_ws_foreground_pending[
                                companion_preset_uid
                            ][
                                "foreground_user_message_id"
                            ] = companion_user_row_id
                        ai_message_id = await chat_history_service.add_ai_message_sync_async(
                            session_id,
                            companion_reply,
                            agent_id=chat.agent_id,
                            meta_data=companion_ai_meta,
                        )
                        response_content = companion_reply
                        if (
                            response_content is None
                            or not str(response_content).strip()
                        ):
                            logger.error(
                                f"Companion chat returned no content - agent_id={agent_id}, user_id={current_user.id}"
                            )
                            raise HTTPException(
                                status_code=500,
                                detail="Chat returned no content",
                            )
                        (
                            response_text_content,
                            response_content_parts,
                        ) = _normalize_chat_response_content(response_content)
                        if companion_ws_inner_tick_ctx is not None:
                            apply_companion_ws_inner_tick_coords(
                                companion_ws_inner_tick_ctx,
                                user_id=current_user.id,
                                agent_id=agent_id,
                                chat_id=agent_scope_inner_tick_chat_id,
                            )

            response_preview = (
                response_text_content[:100]
                if response_text_content
                else f"[multimodal parts={len(response_content_parts or [])}]"
            )
            logger.debug(f"Agent聊天响应成功: {response_preview}...")

        except HTTPException:
            raise
        except CompanionLLMInferenceBackendError:
            raise
        except Exception as e:
            logger.error(f"Agent聊天处理失败: {str(e)}")
            raise

        latest_message_info = None
        try:
            if ai_message_id is not None:
                with log_time(f"获取AI消息信息: message_id={ai_message_id}"):
                    latest_message_info = (
                        await chat_history_service.get_ai_message_info_by_id(
                            db, ai_message_id
                        )
                    )
            if latest_message_info is None:
                with log_time(f"获取最新消息: session_id={session_id}"):
                    latest_message_info = (
                        await chat_history_service.get_latest_ai_message_info(
                            db, session_id
                        )
                    )
        except Exception as e:
            logger.warning(f"获取最新消息信息失败: {str(e)}")

        user_message_id = None
        try:
            with log_time(f"获取最新用户消息ID: session_id={session_id}"):
                user_message_id = (
                    await chat_history_service.get_latest_user_message_id(
                        db, session_id
                    )
                )
        except Exception as e:
            logger.warning(f"获取最新用户消息ID失败: {str(e)}")

        completion = build_companion_ws_completion_data(
            response_text_content=response_text_content,
            response_content_parts=response_content_parts,
            last_user_text=last_user_text,
            latest_message_info=latest_message_info,
            audio_url=None,
            request=request,
            source_imate_id=request.target_imate_id,
            user_message_id=user_message_id,
            subscription_actions=None,
            client_local_id=effective_local_id,
        )

        timing_message = request_handling_timer.stop()
        logger.debug(f"聊天请求完成: agent_id={agent_id}, {timing_message}")

        payload = APIResponse.success(
            data=completion.model_dump(exclude_none=True)
        )
        sl = await _agent_status_line_for_chat_header(db, agent_id)
        out = payload.model_dump(exclude_none=True)
        out["status_line"] = sl
        return out

    except HTTPException:
        raise
    except CompanionLLMInferenceBackendError as exc:
        logger.error(
            "Companion LLM inference backend error provider_http_status={} message={!r}",
            exc.provider_http_status,
            exc.client_message_en,
        )
        raise CompanionInferenceUpstreamHTTPException(
            status_code=502,
            detail=exc.client_message_en,
            ws_extra={
                "error_kind": "llm_inference_backend",
                "llm_provider_http_status": exc.provider_http_status,
            },
        ) from exc
    except Exception as e:
        logger.error(f"聊天请求处理失败: {str(e)}")
        logger.exception("聊天请求异常详细信息:")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.websocket("/ws")
async def chat_completions_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
    voice_svc: VoiceService = Depends(deps.get_voice_service),
):
    # TODO(commercialization-cleanup): Companion subscription / ``record_usage`` / limit checks
    # stay in this WS orchestration layer and ``inner_tick_fire.py`` — never in
    # ``app/core/companion_harness`` (see harness AGENTS.md).
    # Concurrency (see ``session.Coordinator``, ``companion_harness`` AGENTS.md):
    # - Prototype: one signed-on presence per paired user (no multi-tab). Each ``accept()``
    #   is that single wire; turns serialize on scope ``CompanionSession.turn_lock`` (#3272).
    # TODO(companion-ws-single-presence): #3272 — reject or supersede a second ``accept()``
    # on (user_id, agent_id).
    # https://github.com/NascentCore/inty/issues/3272
    await websocket.accept()
    ws_conn_id = _resolve_ws_conn_id_from_websocket(websocket)
    current_user = await _get_current_user_from_websocket(websocket, db)
    if current_user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    current_user = await _resolve_assumed_chat_websocket_user(
        operator=current_user,
        assume_user_id=websocket.query_params.get("assume_user_id"),
        db=db,
    )

    telegram_ws_reject = ws_reject_reason_if_telegram_active(
        user_id=str(current_user.id)
    )
    if telegram_ws_reject is not None:
        await websocket.close(code=4003, reason=telegram_ws_reject[:123])
        return
    register_app_ws_channel(user_id=str(current_user.id))

    app_version_code_header = websocket.headers.get("appVersionCode")
    app_version_code = (
        int(app_version_code_header)
        if app_version_code_header is not None
        and app_version_code_header.isdigit()
        else None
    )

    logger.info(
        "chat_ws session_open ws_conn_id={} user={} path={}",
        ws_conn_id,
        current_user.id,
        websocket.url.path,
    )

    # Business / assistant JSON uses a per-connection queue + pump; control frames bypass the queue
    # (see _handle_chat_websocket_control_json docstring: transport vs logical layer).
    outbound_queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    pump_task = asyncio.create_task(
        chat_ws_outbound_pump(websocket, outbound_queue),
        name="chat_ws_outbound_pump",
    )

    tc_box: list[Optional[dict]] = [None]
    companion_ws = CompanionWebSocketCoordinator.for_current_loop()
    companion_ws.bind_outbound_queue(outbound_queue)
    # TODO(companion-presence-ws-outbound): one session downlink consumer; no extra bootstrap task. #3211 #3398
    bootstrap_interim_consumer_task = asyncio.create_task(
        _companion_ws_bootstrap_interim_consumer(companion_ws),
        name="companion_ws_bootstrap_interim",
    )
    inflight_turn_tracker = ChatWsInflightTurnTracker()
    ChatWsInflightShutdownRegistry.register(inflight_turn_tracker)
    ws_leased_agent_id_box: list[Optional[str]] = [None]
    ws_delivery = inner_tick_delivery_for_ws(outbound_queue)

    async def _ws_tool_background_materializer(
        tool_ev: ToolOutputEvent,
    ) -> WsOutboundPayload:
        ctx = companion_ws.pop_foreground_pending(tool_ev.user_msg_uuid)
        assert ctx is not None
        return await _build_companion_tool_background_ws_payload(
            db=db,
            agent_id=str(ctx["agent_id"]),
            session_id=str(ctx["session_id"]),
            ev=tool_ev,
            request=ctx["request"],
            effective_local_id=ctx["effective_local_id"],
            foreground_user_message_id=ctx.get("foreground_user_message_id"),
        )

    ws_downlink = WebSocketDownlink(
        outbound_queue,
        _ws_tool_background_materializer,
    )
    presence = Session.from_coordinator(
        downlink=ws_downlink,
        coordinator=companion_ws,
    )
    poll_secs = float(
        global_config_loaded_from_config_yaml.app.features.companion_ws_proactive_chat_poll_seconds
    )

    async def _run_ws_inner_tick_poll(ctx: dict[str, Any]) -> None:
        inner_tick_user_for_log = ctx["user_id"]
        try:
            await run_inner_tick_poll(
                delivery=ws_delivery,
                coordinator=companion_ws,
                ws_conn_id=ws_conn_id,
                tc_box=tc_box,
            )
        except Exception:
            logger.exception(
                "companion_ws_inner_tick worker failed ws_conn_id={} user_id={}",
                ws_conn_id,
                inner_tick_user_for_log,
            )

    await presence.start_inner_tick_worker(
        poll_seconds=poll_secs,
        run_one_poll=_run_ws_inner_tick_poll,
    )

    idle = _chat_ws_idle_timeout_seconds()
    try:
        while True:
            recv_task = asyncio.create_task(
                asyncio.wait_for(websocket.receive_text(), timeout=idle)
            )
            queue_task = asyncio.create_task(
                companion_ws.background_events.get()
            )
            done, _pending = await asyncio.wait(
                {recv_task, queue_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if queue_task in done:
                recv_task.cancel()
                try:
                    await recv_task
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                except WebSocketDisconnect:
                    logger.debug(
                        "companion tool_bg receive task disconnected while queue event was ready"
                    )
                except RuntimeError as exc:
                    if _is_ws_receive_text_not_connected_runtime_error(exc):
                        logger.debug(
                            "companion tool_bg receive task ended during queue dispatch: {}",
                            exc,
                        )
                    else:
                        raise
                try:
                    ev = queue_task.result()
                except Exception as exc:
                    logger.warning(
                        f"companion tool_bg queue result failed: {exc}"
                    )
                    continue
                # TODO(observability): missing ctx often means stale user_msg_uuid or lifecycle bug;
                # consider metrics and whether to drop vs dead-letter ToolOutputEvent.
                ctx = companion_ws.pop_foreground_pending(ev.user_msg_uuid)
                if ctx is None:
                    logger.warning(
                        "companion tool_bg missing foreground ctx user_msg_uuid={}",
                        ev.user_msg_uuid,
                    )
                    continue
                # Pop to detect stale uuid; re-set so deliver holds turn_lock without losing ctx.
                companion_ws.set_foreground_pending(ev.user_msg_uuid, ctx)
                scope = companion_scope_from_foreground_ctx(ctx)
                if scope is None:
                    logger.warning(
                        "companion tool_bg missing scope coords user_msg_uuid={}",
                        ev.user_msg_uuid,
                    )
                    continue
                scope_lock = get_scope_turn_lock(scope)
                try:
                    async with scope_lock:
                        await ws_downlink.deliver(
                            tool_background_downlink(tool_output=ev)
                        )
                except Exception:
                    logger.exception("companion tool_bg ws completion failed")
                continue

            queue_task.cancel()
            try:
                await queue_task
            except asyncio.CancelledError:
                pass
            try:
                raw = recv_task.result()
            except asyncio.TimeoutError:
                await websocket.close()
                return
            except WebSocketDisconnect:
                return
            except RuntimeError as exc:
                if _is_ws_receive_text_not_connected_runtime_error(exc):
                    return
                raise
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = None
            if await _try_handle_ws_user_signed_on_frame(
                websocket,
                data,
                db=db,
                current_user=current_user,
                companion_ws=companion_ws,
                inflight_turn_tracker=inflight_turn_tracker,
                ws_conn_id=ws_conn_id,
                ws_leased_agent_id_box=ws_leased_agent_id_box,
                outbound_queue=outbound_queue,
                tc_box=tc_box,
                subscription_svc=subscription_svc,
                voice_svc=voice_svc,
                app_version_code=app_version_code,
            ):
                continue
            if await _try_handle_ws_user_signed_out_frame(
                websocket,
                data,
                db=db,
                current_user=current_user,
                companion_ws=companion_ws,
                inflight_turn_tracker=inflight_turn_tracker,
                subscription_svc=subscription_svc,
                ws_conn_id=ws_conn_id,
                ws_leased_agent_id_box=ws_leased_agent_id_box,
            ):
                continue
            if await _try_handle_ws_ws_conn_dropped_frame(
                websocket,
                data,
                db=db,
                current_user=current_user,
                subscription_svc=subscription_svc,
                ws_conn_id=ws_conn_id,
            ):
                continue
            if await _handle_chat_websocket_control_json(
                websocket, data, tc_box
            ):
                continue
            if not isinstance(data, dict):
                await outbound_queue.put(
                    ChatWebSocketQueuedPlainError(
                        code=400,
                        message="Chat frame must be a JSON object",
                        data=None,
                        agent_id="",
                    ).model_dump()
                )
                continue
            try:
                websocket_request = ChatWebSocketRequest.model_validate(data)
            except ValidationError as exc:
                await outbound_queue.put(
                    ChatWebSocketQueuedPlainError(
                        code=422,
                        message="Invalid chat WebSocket request",
                        data=json.loads(exc.json()),
                        agent_id=str(data.get("agent_id") or ""),
                    ).model_dump()
                )
                continue
            merged_request = _chat_request_with_merged_ws_time_context(
                websocket_request.request,
                tc_box[0],
            )
            try:
                # TODO(companion-presence-chat-gate): reject chat turns when this ws_conn_id
                # does not hold the (user_id, agent_id) lease (clients without user_signed_on).
                # TODO(tool-bg-idle-starves-user-chat): USER_MESSAGE waits on turn_lock after
                # inner-tick workers; if proactive/maintenance holds the lock on tool_bg_idle,
                # the frame is accepted but no chat response is sent (REPL: user-input only).
                # https://github.com/NascentCore/inty/issues/3113
                # https://github.com/NascentCore/inty/issues/3123
                await companion_ws.cancel_implicit_greeting_turn_if_running()
                turn_task = inflight_turn_tracker.spawn(
                    _agent_chat_ws_completions_impl(
                        db=db,
                        agent_id=websocket_request.agent_id,
                        request=merged_request,
                        current_user=current_user,
                        subscription_svc=subscription_svc,
                        voice_svc=voice_svc,
                        companion_background_sink=companion_ws.background_sink,
                        companion_ws_foreground_pending=companion_ws.foreground_pending,
                        companion_ws_inner_tick_ctx=companion_ws.inner_tick_context,
                        companion_ws=companion_ws,
                        ws_outbound_queue=outbound_queue,
                        ws_conn_id=ws_conn_id,
                    ),
                    name=f"chat_ws_turn_{ws_conn_id}",
                )
                response = await turn_task
            except asyncio.CancelledError:
                logger.debug(
                    "chat_ws companion turn cancelled ws_conn_id={} user={}",
                    ws_conn_id,
                    current_user.id,
                )
                break
            except HTTPException as e:
                await outbound_queue.put(
                    _chat_ws_error_payload_from_http_exception(
                        e, agent_id=websocket_request.agent_id
                    )
                )
                continue
            if response is None:
                continue
            if isinstance(response, dict):
                response_data = dict(response)
            else:
                response_data = response.model_dump(exclude_none=True)
            response_data["agent_id"] = websocket_request.agent_id
            await outbound_queue.put(response_data)
    except asyncio.CancelledError:
        logger.debug(
            "chat_ws session cancelled ws_conn_id={} user={}",
            ws_conn_id,
            current_user.id,
        )
        return
    except WebSocketDisconnect:
        return
    finally:
        unregister_app_ws_channel(user_id=str(current_user.id))
        logger.info(
            "chat_ws session_end ws_conn_id={} user={}",
            ws_conn_id,
            current_user.id,
        )
        leased_agent_id = ws_leased_agent_id_box[0]
        if leased_agent_id is not None:
            companion_presence_registry().release(
                current_user.id,
                leased_agent_id,
                ws_conn_id,
            )
            ws_leased_agent_id_box[0] = None
        await presence.stop()
        bootstrap_interim_consumer_task.cancel()
        try:
            await bootstrap_interim_consumer_task
        except asyncio.CancelledError:
            pass
        # TODO(ws-disconnect-lifecycle): #3256 — persist-first; finish turns; mark undelivered.
        await inflight_turn_tracker.cancel_all()
        ChatWsInflightShutdownRegistry.unregister(inflight_turn_tracker)
        await _shutdown_chat_ws_outbound_pump(pump_task)
