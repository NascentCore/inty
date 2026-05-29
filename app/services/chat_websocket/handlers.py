"""Endpoint lifecycle handlers for chat WebSocket routes."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from fastapi import Depends, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.companion.websocket_coordinator import (
    ChatWsInflightShutdownRegistry,
    ChatWsInflightTurnTracker,
    CompanionWebSocketCoordinator,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.core.model_selection import select_chat_model
from app.schemas.chat_websocket import (
    ChatWebSocketQueuedPlainError,
    ChatWebSocketRequest,
)
from app.schemas.response import APIResponse
from app.services import agent_service
from app.services.agentic_companion.downlink import tool_background_downlink
from app.services.agentic_companion.inner_tick_delivery import inner_tick_delivery_for_ws
from app.services.agentic_companion.inner_tick_poll import run_inner_tick_poll
from app.services.agentic_companion.session import Session
from app.services.agentic_companion.ws_downlink import WebSocketDownlink
from app.services.chat_websocket.auth import (
    _get_current_user_from_websocket,
    _resolve_assumed_chat_websocket_user,
)
from app.services.chat_websocket.bootstrap import _companion_ws_bootstrap_interim_consumer
from app.services.chat_websocket.frames import (
    _handle_chat_websocket_control_json,
    _try_handle_ws_user_signed_on_frame,
    _try_handle_ws_user_signed_out_frame,
    _try_handle_ws_ws_conn_dropped_frame,
)
from app.services.chat_websocket.transport import (
    _chat_ws_idle_timeout_seconds,
    _is_ws_receive_text_not_connected_runtime_error,
    _resolve_ws_conn_id_from_websocket,
    _shutdown_chat_ws_outbound_pump,
)
from app.services.chat_websocket.turn import (
    _agent_chat_ws_completions_impl,
    _build_companion_tool_background_ws_payload,
    _chat_request_with_merged_ws_time_context,
    _chat_ws_error_payload_from_http_exception,
)
from app.services.chat_websocket.verify import _verify_ws_simple_llm_reply
from app.services.chat_websocket_session import chat_ws_outbound_pump
from app.services.subscription_service import SubscriptionService
from app.services.voice_service import VoiceService
from app.services.ws_session_messages import WsOutboundPayload
from app.api.v1.endpoints.chat import (
    _agent_status_line_for_chat_header,
    _build_chat_response,
    _normalize_chat_response_content,
)

async def run_chat_completions_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
    voice_svc: VoiceService = Depends(deps.get_voice_service),
):
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
    companion_ws.bind_outbound_queue(outbound_queue)
    # TODO(companion-presence-ws-outbound): one session downlink consumer; no extra bootstrap task. #3211
    bootstrap_interim_consumer_task = asyncio.create_task(
        _companion_ws_bootstrap_interim_consumer(companion_ws),
        name="companion_ws_bootstrap_interim",
    )
    inflight_turn_tracker = ChatWsInflightTurnTracker()
    ChatWsInflightShutdownRegistry.register(inflight_turn_tracker)
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
                ctx=ctx,
                delivery=ws_delivery,
                subscription_svc=subscription_svc,
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
                try:
                    async with companion_ws.turn_lock:
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
                            companion_ws=companion_ws,
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
        await presence.stop()
        bootstrap_interim_consumer_task.cancel()
        try:
            await bootstrap_interim_consumer_task
        except asyncio.CancelledError:
            pass
        # TODO(ws-disconnect-lifecycle): do not cancel on disconnect; finish turns and mark chat_history undelivered.
        await inflight_turn_tracker.cancel_all()
        ChatWsInflightShutdownRegistry.unregister(inflight_turn_tracker)
        await _shutdown_chat_ws_outbound_pump(pump_task)

async def run_chat_completions_websocket_verify(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
):
    """
    Legacy smoke endpoint: same **outbound queue + pump** as ``/ws`` (FIFO business JSON).

    Per chat frame: **one** ``chat.completions`` call with system + user messages only (via
    ``get_chat_openai_client``). No ``Agent`` runtime, no companion pipeline, no chat_history
    persistence. Use to validate transport, queue behavior, and minimal LLM connectivity.
    """
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
