"""Production companion WebSocket session loop for ``/ws``."""

import asyncio
import json
from typing import Any, Optional

from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.v1.endpoints.chat_ws.auth import (
    _get_current_user_from_websocket,
    _resolve_assumed_chat_websocket_user,
    _resolve_ws_conn_id_from_websocket,
)
from app.api.v1.endpoints.chat_ws.companion_turn import _agent_chat_ws_completions_impl
from app.api.v1.endpoints.chat_ws.control_frames import _handle_chat_websocket_control_json
from app.api.v1.endpoints.chat_ws.inner_tick import (
    _try_fire_companion_ws_maintenance_inner_tick,
    _try_fire_companion_ws_proactive_chat,
    _try_fire_companion_ws_scheduled_task_inner_tick,
)
from app.api.v1.endpoints.chat_ws.lifecycle_frames import (
    _try_handle_ws_user_signed_on_frame,
    _try_handle_ws_user_signed_out_frame,
    _try_handle_ws_ws_conn_dropped_frame,
)
from app.api.v1.endpoints.chat_ws.time_context import _chat_request_with_merged_ws_time_context
from app.api.v1.endpoints.chat_ws.tool_background import _build_companion_tool_background_ws_payload
from app.api.v1.endpoints.chat_ws.transport import (
    _chat_ws_error_payload_from_http_exception,
    _chat_ws_idle_timeout_seconds,
    _is_ws_receive_text_not_connected_runtime_error,
    _shutdown_chat_ws_outbound_pump,
)
from app.core.companion_harness.companion.websocket_coordinator import (
    ChatWsInflightShutdownRegistry,
    ChatWsInflightTurnTracker,
    CompanionWebSocketCoordinator,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.chat_websocket import ChatWebSocketQueuedPlainError, ChatWebSocketRequest
from app.services.chat_websocket_session import chat_ws_outbound_pump
from app.services.subscription_service import SubscriptionService
from app.services.voice_service import VoiceService
from app.services.ws_session_messages import WsOutboundPayload

async def run_companion_chat_ws_session(
    websocket: WebSocket,
    db: AsyncSession,
    subscription_svc: SubscriptionService,
    voice_svc: VoiceService,
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
    inflight_turn_tracker = ChatWsInflightTurnTracker()
    ChatWsInflightShutdownRegistry.register(inflight_turn_tracker)
    inner_tick_worker_stop = asyncio.Event()

    async def companion_ws_inner_tick_worker() -> None:
        while not inner_tick_worker_stop.is_set():
            feats = global_config_loaded_from_config_yaml.app.features
            poll = float(feats.companion_ws_proactive_chat_poll_seconds)
            try:
                await asyncio.wait_for(
                    inner_tick_worker_stop.wait(), timeout=poll
                )
                break
            except asyncio.TimeoutError:
                pass
            inner_tick_snapshot: dict[str, Any] | None = None
            async with companion_ws.turn_lock:
                inner_tick_snapshot = companion_ws.snapshot_inner_tick_coords()
                if inner_tick_snapshot is not None:
                    companion_ws.clear_ws_inner_tick_proactive_tool_bg_idle_if_idle()
            if inner_tick_snapshot is None:
                logger.debug(
                    "companion_ws_inner_tick_poll no_inner_tick_coords ws_conn_id={}",
                    ws_conn_id,
                )
                continue
            logger.debug(
                "companion_ws_inner_tick_poll inner_tick_coords ws_conn_id={} user={} agent={} chat_id={}",
                ws_conn_id,
                inner_tick_snapshot.get("user_id"),
                inner_tick_snapshot.get("agent_id"),
                inner_tick_snapshot.get("chat_id"),
            )
            inner_tick_user_for_log = inner_tick_snapshot["user_id"]
            try:
                await _try_fire_companion_ws_scheduled_task_inner_tick(
                    outbound_queue=outbound_queue,
                    ctx=inner_tick_snapshot,
                    subscription_svc=subscription_svc,
                    companion_ws=companion_ws,
                    ws_conn_id=ws_conn_id,
                    tc_box=tc_box,
                )
                await _try_fire_companion_ws_proactive_chat(
                    outbound_queue=outbound_queue,
                    ctx=inner_tick_snapshot,
                    subscription_svc=subscription_svc,
                    companion_ws=companion_ws,
                    ws_conn_id=ws_conn_id,
                    tc_box=tc_box,
                )
                if feats.companion_ws_maintenance_inner_tick_enabled:
                    await _try_fire_companion_ws_maintenance_inner_tick(
                        outbound_queue=outbound_queue,
                        ctx=inner_tick_snapshot,
                        subscription_svc=subscription_svc,
                        companion_ws=companion_ws,
                        ws_conn_id=ws_conn_id,
                        tc_box=tc_box,
                    )
            except Exception:
                logger.exception(
                    "companion_ws_inner_tick worker failed ws_conn_id={} user_id={}",
                    ws_conn_id,
                    inner_tick_user_for_log,
                )

    hb_worker_task = asyncio.create_task(
        companion_ws_inner_tick_worker(),
        name="companion_ws_inner_tick",
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
                try:
                    async with companion_ws.turn_lock:
                        bg_payload = (
                            await _build_companion_tool_background_ws_payload(
                                db=db,
                                agent_id=str(ctx["agent_id"]),
                                session_id=str(ctx["session_id"]),
                                ev=ev,
                                request=ctx["request"],
                                effective_local_id=ctx["effective_local_id"],
                                foreground_user_message_id=ctx.get(
                                    "foreground_user_message_id"
                                ),
                            )
                        )
                        await outbound_queue.put(bg_payload)
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
            ):
                continue
            if await _try_handle_ws_ws_conn_dropped_frame(
                websocket,
                data,
                db=db,
                current_user=current_user,
                companion_ws=companion_ws,
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
                # TODO(tool-bg-idle-starves-user-chat): USER_MESSAGE waits on turn_lock after
                # inner-tick workers; if proactive/maintenance holds the lock on tool_bg_idle,
                # the frame is accepted but no chat response is sent (REPL: user-input only).
                # https://github.com/NascentCore/inty/issues/3113
                # https://github.com/NascentCore/inty/issues/3123
                await companion_ws.cancel_implicit_greeting_turn_if_running()
                async with companion_ws.turn_lock:
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
                            ws_outbound_queue=outbound_queue,
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
            if isinstance(response, dict):
                response_data = dict(response)
            else:
                response_data = response.model_dump(exclude_none=True)
            response_data["agent_id"] = websocket_request.agent_id
            await outbound_queue.put(response_data)
    except WebSocketDisconnect:
        return
    finally:
        logger.info(
            "chat_ws session_end ws_conn_id={} user={}",
            ws_conn_id,
            current_user.id,
        )
        inner_tick_worker_stop.set()
        hb_worker_task.cancel()
        try:
            await hb_worker_task
        except asyncio.CancelledError:
            pass
        # TODO(ws-disconnect-lifecycle): do not cancel on disconnect; finish turns and mark chat_history undelivered.
        await inflight_turn_tracker.cancel_all()
        ChatWsInflightShutdownRegistry.unregister(inflight_turn_tracker)
        await _shutdown_chat_ws_outbound_pump(pump_task)
