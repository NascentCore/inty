"""Companion turn execution and response materialization for chat WebSocket sessions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from fastapi import HTTPException
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.companion.llm_inference_errors import (
    CompanionLLMInferenceBackendError,
)
from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutputSink,
)
from app.core.companion_harness.companion.websocket_coordinator import (
    BootstrapInterimDeliverCtx,
    CompanionWebSocketCoordinator,
    apply_companion_ws_inner_tick_coords,
)
from app.core.companion_harness.tools.image_gate import (
    generated_image_meta_from_index_slice,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.core.model_selection import select_chat_model
from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat import ChatCompletionRequest, UserTimeContext
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    chat_ws_queued_error_dict,
    dump_chat_ws_companion_wire_meta,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.schemas.response import APIResponse
from app.schemas.user import User as UserSchema
from app.services import agent_service, chat_history_service, chat_service
from app.services import companion_chat_service
from app.services.chat_service import generate_session_id
from app.services.phone_call_service import (
    PhoneCallConfigError,
    PhoneCallLimitError,
    phone_call_service,
)
from app.services.subscription_service import SubscriptionService
from app.services.voice_service import VoiceService, voice_service as default_voice_service
from app.services.ws_session_messages import WsOutboundPayload
from app.utils.timing import Timer, log_time
from app.api.v1.endpoints.chat import (
    CompanionInferenceUpstreamHTTPException,
    _agent_status_line_for_chat_header,
    _build_chat_response,
    _companion_ai_meta_from_turn_result,
    _companion_rejects_multimodal_user_turn,
    _normalize_chat_response_content,
    _persist_companion_user_message_for_bg,
    _require_websocket_companion_message_id_uuid,
)

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
    # TODO(issue#3208): emit ChatWebSocketQueuedSuccessFrame via typed builder.
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
    data = _build_chat_response(
        ev.text,
        None,
        "",
        latest_message_info,
        None,
        request,
        source_imate_id=request.target_imate_id,
        user_message_id=user_message_id,
        subscription_actions=subscription_actions,
        client_local_id=effective_local_id,
    )
    payload = APIResponse.success(data=data)
    out = payload.model_dump(exclude_none=True)
    out["agent_id"] = agent_id
    out["status_line"] = await _agent_status_line_for_chat_header(db, agent_id)
    return out


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
) -> dict:
    """One companion chat turn for ``/api/v1/chat/ws`` (production WebSocket path).

    Companion kernel + wire envelope.
    HTTP-era extras (chat limit gate, legacy TTS, usage accounting, push read side-effects,
    surprise snap, in-frame memory prompts) stay on ``_agent_chat_completions_impl`` or other routes.
    """
    # TODO(cleanup-ws-http-chat-impl): Deduplicate post-turn finalize with HTTP impl where shared.
    # TODO(issue#3208): return ChatWebSocketQueuedSuccessFrame via typed builder.
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
                            chat_id=chat.id,
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
                            "request": request,
                            "effective_local_id": effective_local_id,
                            "user_id": str(current_user.id),
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
                        # TODO(companion-presence-ws-outbound): deliver via session, not coordinator queue. #3211 #3209
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
                        bootstrap_interim_sink = (
                            companion_ws.bootstrap_interim_output_sink()
                        )
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
                                defer_memory_update=True,
                                session_id=session_id,
                                background_output_sink=companion_background_sink,
                                preset_user_msg_uuid=companion_preset_uid,
                            )
                        else:
                            companion_turn = await companion_chat_service.run_user_chat(
                                user_id=current_user.id,
                                agent_id=agent_id,
                                chat_id=chat.id,
                                user_text=last_user_text,
                                resolved_chat_model=model_override,
                                defer_memory_update=True,
                                session_id=session_id,
                                background_output_sink=companion_background_sink,
                                preset_user_msg_uuid=companion_preset_uid,
                                implicit_signal_bundle=companion_implicit_bundle,
                                bootstrap_interim_output_sink=bootstrap_interim_sink,
                            )
                        if (
                            companion_preset_uid is not None
                            and companion_ws_foreground_pending is not None
                            and not companion_turn.tool_background_started
                        ):
                            companion_ws_foreground_pending.pop(
                                companion_preset_uid, None
                            )
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
                            companion_ws_foreground_pending.pop(
                                companion_preset_uid, None
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
                    companion_reply = companion_turn.assistant_text
                    companion_ai_meta = _companion_ai_meta_from_turn_result(
                        companion_turn
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
                        companion_ws_foreground_pending[companion_preset_uid][
                            "foreground_user_message_id"
                        ] = companion_user_row_id
                    ai_message_id = (
                        await chat_history_service.add_ai_message_sync_async(
                            session_id,
                            companion_reply,
                            agent_id=chat.agent_id,
                            meta_data=companion_ai_meta,
                        )
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
                            status_code=500, detail="Chat returned no content"
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
                            chat_id=chat.id,
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

        data = _build_chat_response(
            response_text_content,
            response_content_parts,
            last_user_text,
            latest_message_info,
            None,
            request,
            source_imate_id=request.target_imate_id,
            user_message_id=user_message_id,
            subscription_actions=None,
            client_local_id=effective_local_id,
        )

        timing_message = request_handling_timer.stop()
        logger.debug(f"聊天请求完成: agent_id={agent_id}, {timing_message}")

        payload = APIResponse.success(data=data)
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
