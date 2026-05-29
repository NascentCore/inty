"""Control and presence frame handlers for chat WebSocket sessions."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import HTTPException, WebSocket
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.companion.runtime_events import (
    build_user_signed_out_runtime_event_record,
    build_ws_conn_dropped_runtime_event_record,
)
from app.core.companion_harness.companion.websocket_coordinator import (
    ChatWsInflightTurnTracker,
    CompanionWebSocketCoordinator,
)
from app.core.model_selection import select_chat_model
from app.schemas.chat import ChatCompletionRequest, ChatMessage, UserTimeContext
from app.schemas.chat_websocket import (
    ChatWsClientContextAckFrame,
    ChatWsPongFrame,
    ChatWsUserSignedOnAckFrame,
    ChatWsUserSignedOnFrame,
    ChatWsUserSignedOutAckFrame,
    ChatWsUserSignedOutFrame,
    ChatWsWsConnDroppedFrame,
    normalize_websocket_companion_message_id_uuid,
)
from app.schemas.user import User as UserSchema
from app.services import chat_service, companion_chat_service
from app.services.subscription_service import SubscriptionService
from app.services.voice_service import VoiceService
from app.services.ws_session_messages import WsOutboundPayload
from app.services.chat_websocket.turn import (
    _agent_chat_ws_completions_impl,
    _chat_request_with_merged_ws_time_context,
    _chat_ws_error_payload_from_http_exception,
)

async def _enqueue_companion_greeting_ws_turn_after_user_signed_on(
    *,
    db: AsyncSession,
    agent_id: str,
    preset_message_id: str,
    current_user: UserSchema,
    app_version_code: Optional[int],
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
            async with companion_ws.turn_lock:
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
    companion_ws: CompanionWebSocketCoordinator | None,
    inflight_turn_tracker: ChatWsInflightTurnTracker | None,
    ws_conn_id: str,
    outbound_queue: asyncio.Queue[WsOutboundPayload] | None = None,
    tc_box: list[Optional[dict]] | None = None,
    subscription_svc: SubscriptionService | None = None,
    voice_svc: VoiceService | None = None,
    app_version_code: Optional[int] = None,
) -> bool:
    """
    Consume ``{"type":"user_signed_on","agent_id":...}``.

    Product intent: arms inner-tick WebSocket coordinates (proactive chat, maintenance inner-tick,
    and due ``schedule_queue`` reminders share this registration). Requires ``message_id`` (RFC4122);
    missing/invalid ids fail before ack; greeting turn is scheduled before ``user_signed_on_ack``.

    ``/ws/verify`` passes ``companion_ws=None`` and receives ``ok: false`` (not supported).
    """
    if not isinstance(data, dict) or data.get("type") != "user_signed_on":
        return False
    if companion_ws is None:
        await websocket.send_json(
            ChatWsUserSignedOnAckFrame(
                ok=False,
                reason="not_supported",
            ).model_dump(exclude_none=True)
        )
        return True
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
    try:
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        if chat.agent_id != agent_id:
            await websocket.send_json(
                ChatWsUserSignedOnAckFrame(
                    ok=False,
                    reason="agent_mismatch",
                ).model_dump(exclude_none=True)
            )
            return True
        companion_ws.store_inner_tick_coords(
            user_id=current_user.id,
            agent_id=agent_id,
            chat_id=chat.id,
        )
        greeting_scheduled = False
        if (
            outbound_queue is None
            or tc_box is None
            or subscription_svc is None
            or voice_svc is None
        ):
            logger.error(
                "chat_ws user_signed_on greeting missing ws deps ws_conn_id={} agent_id={}",
                ws_conn_id,
                agent_id,
            )
        else:
            assert inflight_turn_tracker is not None
            greeting_task = inflight_turn_tracker.spawn(
                _enqueue_companion_greeting_ws_turn_after_user_signed_on(
                    db=db,
                    agent_id=agent_id,
                    preset_message_id=preset_mid,
                    current_user=current_user,
                    app_version_code=app_version_code,
                    subscription_svc=subscription_svc,
                    voice_svc=voice_svc,
                    companion_ws=companion_ws,
                    tc_box=tc_box,
                    outbound_queue=outbound_queue,
                ),
                name=f"chat_ws_user_signed_on_greeting_{ws_conn_id}",
            )
            companion_ws.register_implicit_greeting_turn(greeting_task)
            greeting_scheduled = True
        await websocket.send_json(
            ChatWsUserSignedOnAckFrame(ok=True).model_dump(exclude_none=True)
        )
        logger.info(
            "chat_ws user_signed_on armed inner_tick coords ws_conn_id={} user={} agent={} "
            "chat_id={} received_message_uuid={} greeting_scheduled={}",
            ws_conn_id,
            current_user.id,
            agent_id,
            chat.id,
            preset_mid,
            greeting_scheduled,
        )
    except Exception:
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
    companion_ws: CompanionWebSocketCoordinator | None,
    inflight_turn_tracker: ChatWsInflightTurnTracker | None,
    subscription_svc: SubscriptionService,
    ws_conn_id: str,
) -> bool:
    """
    Consume ``{"type":"user_signed_out","agent_id":...}``.

    Validates the frame, cancels detached companion turns on this connection, disarms inner-tick
    coords (pauses proactive/maintenance until the next ``user_signed_on``), appends a
    ``user_signed_out`` row to companion ``.companion_runtime_events.jsonl`` (MemoryStore), then
    sends ``user_signed_out_ack``. Does not alter transcript or companion scope persistence.

    ``/ws/verify`` passes ``companion_ws=None`` and receives ``ok: false`` (not supported).
    """
    if not isinstance(data, dict) or data.get("type") != "user_signed_out":
        return False
    if companion_ws is None:
        await websocket.send_json(
            ChatWsUserSignedOutAckFrame(
                ok=False,
                reason="not_supported",
            ).model_dump(exclude_none=True)
        )
        return True
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
        if inflight_turn_tracker is not None:
            # TODO(ws-disconnect-lifecycle): do not cancel; finish turns and mark chat_history undelivered.
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
    companion_ws: CompanionWebSocketCoordinator | None,
    subscription_svc: SubscriptionService,
    ws_conn_id: str,
) -> bool:
    """
    Consume ``{"type":"ws_conn_dropped","agent_id":...,"dropped_at_utc":...}``.

    Appends a ``ws_conn_dropped`` row to companion ``.companion_runtime_events.jsonl`` (MemoryStore).
    Does not alter inner-tick coords or transcript.

    ``/ws/verify`` passes ``companion_ws=None`` and receives ``ok: false`` (not supported).
    """
    if not isinstance(data, dict) or data.get("type") != "ws_conn_dropped":
        return False
    if companion_ws is None:
        await websocket.send_json(
            {
                "type": "ws_conn_dropped_ack",
                "ok": False,
                "reason": "not_supported",
            }
        )
        return True
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
