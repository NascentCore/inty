"""Legacy ``/ws/verify`` WebSocket session loop (minimal LLM, no companion harness)."""

import asyncio
import json
from typing import Optional

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.chat import (
    _agent_status_line_for_chat_header,
    _build_chat_response,
    _normalize_chat_response_content,
)
from app.api.v1.endpoints.chat_ws.auth import (
    _get_current_user_from_websocket,
    _resolve_assumed_chat_websocket_user,
    _resolve_ws_conn_id_from_websocket,
)
from app.api.v1.endpoints.chat_ws.control_frames import _handle_chat_websocket_control_json
from app.api.v1.endpoints.chat_ws.lifecycle_frames import (
    _try_handle_ws_user_signed_on_frame,
    _try_handle_ws_user_signed_out_frame,
    _try_handle_ws_ws_conn_dropped_frame,
)
from app.api.v1.endpoints.chat_ws.time_context import _chat_request_with_merged_ws_time_context
from app.api.v1.endpoints.chat_ws.transport import (
    _chat_ws_idle_timeout_seconds,
    _is_ws_receive_text_not_connected_runtime_error,
    _shutdown_chat_ws_outbound_pump,
)
from app.api.v1.endpoints.chat_ws.verify_llm import _verify_ws_simple_llm_reply
from app.core.model_selection import select_chat_model
from app.schemas.chat_websocket import ChatWebSocketQueuedPlainError, ChatWebSocketRequest
from app.schemas.response import APIResponse
from app.services import agent_service
from app.services.chat_websocket_session import chat_ws_outbound_pump
from app.services.subscription_service import SubscriptionService
from app.services.ws_session_messages import WsOutboundPayload

async def run_companion_chat_ws_verify_session(
    websocket: WebSocket,
    db: AsyncSession,
    subscription_svc: SubscriptionService,
) -> None:
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

    logger.info(
        "chat_ws_verify session_open ws_conn_id={} user={} path={}",
        ws_conn_id,
        current_user.id,
        websocket.url.path,
    )

    outbound_queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    pump_task = asyncio.create_task(
        chat_ws_outbound_pump(websocket, outbound_queue),
        name="chat_ws_verify_outbound_pump",
    )
    tc_box: list[Optional[dict]] = [None]
    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=_chat_ws_idle_timeout_seconds(),
                )
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
                companion_ws=None,
                inflight_turn_tracker=None,
                ws_conn_id=ws_conn_id,
            ):
                continue
            if await _try_handle_ws_user_signed_out_frame(
                websocket,
                data,
                db=db,
                current_user=current_user,
                companion_ws=None,
                inflight_turn_tracker=None,
                subscription_svc=subscription_svc,
                ws_conn_id=ws_conn_id,
            ):
                continue
            if await _try_handle_ws_ws_conn_dropped_frame(
                websocket,
                data,
                db=db,
                current_user=current_user,
                companion_ws=None,
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
            agent_id = websocket_request.agent_id
            request = _chat_request_with_merged_ws_time_context(
                websocket_request.request,
                tc_box[0],
            )

            user_messages = [
                msg for msg in request.messages if msg.role == "user"
            ]
            if not user_messages:
                await outbound_queue.put(
                    ChatWebSocketQueuedPlainError(
                        code=400,
                        message="No user message found",
                        data=None,
                        agent_id=agent_id,
                    ).model_dump()
                )
                continue

            last_user_text = user_messages[-1].extract_text_content()

            agent_row = await agent_service.get_agent_for_chat(
                db, agent_id=agent_id
            )
            if not agent_row:
                await outbound_queue.put(
                    ChatWebSocketQueuedPlainError(
                        code=404,
                        message="Agent not found",
                        data=None,
                        agent_id=agent_id,
                    ).model_dump()
                )
                continue

            subscription = await subscription_svc.get_user_current_subscription(
                db, current_user.id
            )
            is_subscribed = bool(subscription)
            model_override = select_chat_model(
                user=current_user, is_subscribed=is_subscribed
            )

            effective_local_id = (
                request.local_id or request.message_id or ""
            ).strip() or None

            try:
                response_text = await _verify_ws_simple_llm_reply(
                    agent_row=agent_row,
                    user_text=last_user_text or "",
                    model_name=model_override.id_on_provider,
                )
            except Exception as e:
                logger.exception("ws/verify simple chat.completions failed")
                await outbound_queue.put(
                    ChatWebSocketQueuedPlainError(
                        code=500,
                        message=str(e),
                        data=None,
                        agent_id=agent_id,
                    ).model_dump()
                )
                continue

            response_text_content, response_content_parts = (
                _normalize_chat_response_content(response_text)
            )
            data = _build_chat_response(
                response_text_content,
                response_content_parts,
                last_user_text or "",
                latest_message_info=None,
                audio_url=None,
                request=request,
                source_imate_id=request.target_imate_id,
                user_message_id=None,
                subscription_actions=[],
                client_local_id=effective_local_id,
            )
            response = APIResponse.success(data=data)
            response_data = response.model_dump(exclude_none=True)
            response_data["agent_id"] = agent_id
            response_data["status_line"] = (
                await _agent_status_line_for_chat_header(db, agent_id)
            )
            await outbound_queue.put(response_data)
    except WebSocketDisconnect:
        return
    finally:
        logger.info(
            "chat_ws_verify session_end ws_conn_id={} user={}",
            ws_conn_id,
            current_user.id,
        )
        await _shutdown_chat_ws_outbound_pump(pump_task)
