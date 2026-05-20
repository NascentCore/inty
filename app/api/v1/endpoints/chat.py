"""HTTP chat completions and shared chat response helpers (maintenance-mode REST).

Companion WebSocket ``/api/v1/chat/ws`` lives in ``chat_ws.py`` (production harness path).
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable, List, Literal, Optional, TypeAlias, Union

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from langchain_core.messages import HumanMessage
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.chat_settings import ChatSettings
from app.api import deps
from app.api.tags import ANDROID_APP_TAG, INTY_EVAL_TAG, WEB_APP_TAG
from app.schemas.biz_action import (
    GENERAL_SUBSCRIPTION_POPUP_MESSAGES,
    ActionType,
    BizAction,
)
from app.api.utils.feature_gating import (
    is_daily_memory_enabled,
    is_festival_memory_enabled,
)
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.companion.proactive_chat import (
    PROACTIVE_CHAT_SILENT_TOKEN,
    PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER,
    ProactiveChatConfig,
    next_proactive_chat_wait_seconds,
)
from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    next_inner_tick_wait_seconds,
)
from app.core.companion_harness.companion.llm_inference_errors import (
    CompanionLLMInferenceBackendError,
)
from app.core.companion_harness.tools.image_gate import (
    generated_image_meta_from_index_slice,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnResult,
    MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.core.companion_harness.companion.schedule_queue import (
    mark_task_fired,
    mark_task_retry,
    next_due_task_for_execution,
    scheduled_task_synthetic_user_text,
)
from app.core.companion_harness.companion.runtime_events import (
    build_user_signed_out_runtime_event_record,
    build_ws_conn_dropped_runtime_event_record,
)
from app.core.companion_harness.companion.websocket_coordinator import (
    ChatWsInflightShutdownRegistry,
    ChatWsInflightTurnTracker,
    CompanionWebSocketCoordinator,
    apply_companion_ws_inner_tick_coords,
)
from app.core.model_selection import select_chat_model
from app.models.user import AuthType, User
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
    UserTimeContext,
)
from app.schemas.chat_websocket import (
    ChatWebSocketQueuedPlainError,
    ChatWebSocketRequest,
    ChatWsClientContextAckFrame,
    ChatWsCompanionWireMetaData,
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
from app.schemas.response import (
    BizError,
    BusinessErrorCode,
    UsageLimitExceeded,
    create_business_error_response,
)
from app.services import agent_service, chat_history_service, chat_service
from app.services import companion_chat_service
from app.services.chat_assistant_voice import synthesize_chat_assistant_audio
from app.services.chat_ws_voice_message import (
    ChatWsVoiceMessageTtsInput,
    synthesize_chat_ws_voice_message,
)
from app.services.chat_websocket_session import chat_ws_outbound_pump
from app.services.ws_session_messages import WsOutboundPayload
from app.services.memory_service import (
    deliver_daily_memories_for_user_agent,
    deliver_festival_memories_for_user_agent,
)
from app.db.session import AsyncSessionLocal
from app.services.phone_call_service import (
    PhoneCallConfigError,
    PhoneCallLimitError,
    phone_call_service,
)
from app.services.chat_service import generate_session_id
from app.services.subscription_service import SubscriptionService
from app.services.surprise_snap_service import (
    get_unlocked_surprise_snap_message_ids,
    try_trigger_surprise_snap,
)
from app.services.push_notification_service import (
    mark_user_push_notifications_as_read,
)
from app.services.voice_service import (
    GENDER_VOICE_MAPPING,
    VoiceService,
    get_voice_message_narration_mode_from_agent_settings,
    voice_service as default_voice_service,
)
from app.utils.openai_client import get_chat_openai_client
from app.utils.timing import Timer, log_time
from app.schemas.chat import ChatImageGenerationRequest
from app.schemas.chat import ChatImageGenerationResponse
from app.schemas.chat import ChatMusicGenerationRequest
from app.schemas.chat import ChatMusicGenerationResponse
from app.schemas.response import APIResponse
from app.schemas.user import User as UserSchema

router = APIRouter(prefix="/chat", route_class=LoggerRoute)


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



async def _handle_subscription_limit_error(
    session_id: str,
    last_user_message: str | List[dict[str, Any]],
    current_user: UserSchema,
    used_count: int,
    daily_limit: int,
    client_local_id: Optional[str] = None,
) -> APIResponse:
    """处理订阅限制错误"""
    try:
        meta = (
            dump_chat_ws_companion_wire_meta(
                ChatWsCompanionWireMetaData(local_id=client_local_id)
            )
            if client_local_id
            else None
        )
        await chat_history_service.add_user_message_async(
            session_id, last_user_message, meta_data=meta
        )
        logger.debug(f"用户消息已保存到历史记录: {session_id}")
    except Exception as e:
        logger.warning(f"保存用户消息失败: {str(e)}")

    limit_extra: dict[str, Any] = {
        "used_count": used_count,
        "daily_limit": daily_limit,
    }
    if client_local_id:
        limit_extra["local_id"] = client_local_id

    if current_user.auth_type == AuthType.GUEST:
        return create_business_error_response(
            error_info=BusinessErrorCode.GUEST_LOGIN_REQUIRED,
            extra_data=limit_extra,
        )
    return create_business_error_response(
        error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED,
        extra_data=limit_extra,
    )


def _build_surprise_snap_choice_message(
    info: dict,
    unlocked_message_ids: set,
) -> dict:
    """构建单条 Surprise Snap choice 的 message 字典，与消息列表中 surprise_snap 项结构一致。is_locked 仅根据是否在 unlock 表中。"""
    message_id = info.get("id")
    is_locked = not (message_id in unlocked_message_ids)
    return {
        "role": None,
        "content": "",
        "type": "surprise_snap",
        "id": message_id,
        "media_url": info.get("media_url"),
        "caption": info.get("caption") or "",
        "price": info.get("price", 0),
        "is_locked": is_locked,
        "meta_data": info.get("meta_data"),
        "timestamp": info.get("timestamp"),
    }


def _build_festival_prompt_choice_message(
    item: dict, info: Optional[dict]
) -> dict:
    """构建单条节日提醒 choice 的 message 字典，与普通 AI 消息结构一致（含 id、meta_data、timestamp、audio_url）。

    同一条 message 中可能同时出现顶层的 festival_memory_id（snake_case）与 meta_data 内的
    festivalMemoryId（camelCase）：前者为本接口显式提供、供客户端优先使用；后者来自写入
    chat_history 时存储的 meta_data，透传未改。客户端应以顶层 festival_memory_id 为准。
    """
    if info:
        return {
            "role": None,
            "content": item["content"],
            "type": "festival_memory_prompt",
            "festival_memory_id": item["memory_id"],
            "id": info["id"],
            "meta_data": info["meta_data"],
            "timestamp": info["timestamp"],
            "audio_url": info["audio_url"],
        }
    msg_id = item.get("message_id")
    return {
        "role": None,
        "content": item["content"],
        "type": "festival_memory_prompt",
        "festival_memory_id": item["memory_id"],
        "id": msg_id,
        "meta_data": None,
        "timestamp": None,
        "audio_url": None,
    }


def _build_daily_prompt_choice_message(
    item: dict, info: Optional[dict]
) -> dict:
    """构建单条日常记忆提醒 choice 的 message 字典。"""
    if info:
        return {
            "role": None,
            "content": item["content"],
            "type": "daily_memory_prompt",
            "daily_memory_id": item["memory_id"],
            "id": info["id"],
            "meta_data": info["meta_data"],
            "timestamp": info["timestamp"],
            "audio_url": info["audio_url"],
        }
    msg_id = item.get("message_id")
    return {
        "role": None,
        "content": item["content"],
        "type": "daily_memory_prompt",
        "daily_memory_id": item["memory_id"],
        "id": msg_id,
        "meta_data": None,
        "timestamp": None,
        "audio_url": None,
    }


def _normalize_response_content_part(part: Any) -> Optional[dict[str, Any]]:
    if hasattr(part, "model_dump"):
        part = part.model_dump(exclude_none=True)
    if not isinstance(part, dict):
        return None

    part_type = part.get("type")
    if part_type == "text":
        text = part.get("text")
        if isinstance(text, str):
            return {"type": "text", "text": text}
        return None

    if part_type == "image_url":
        image_url = part.get("image_url")
        if hasattr(image_url, "model_dump"):
            image_url = image_url.model_dump(exclude_none=True)
        if not isinstance(image_url, dict):
            return None
        url = image_url.get("url")
        if isinstance(url, str) and url.strip():
            return {"type": "image_url", "image_url": {"url": url}}
        return None

    return None


def _normalize_chat_response_content(
    response_content: Any,
) -> tuple[str, Optional[List[dict[str, Any]]]]:
    if isinstance(response_content, str):
        return response_content, None

    if isinstance(response_content, list):
        normalized_parts: List[dict[str, Any]] = []
        text_parts: List[str] = []
        for part in response_content:
            normalized_part = _normalize_response_content_part(part)
            if normalized_part is None:
                continue
            normalized_parts.append(normalized_part)
            if normalized_part["type"] == "text":
                text = normalized_part.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
        if len(normalized_parts) > 0:
            return "\n".join(text_parts), normalized_parts
        return "", None

    if response_content is None:
        return "", None
    return str(response_content), None


def _build_chat_response(
    response_text_content: str,
    response_content_parts: Optional[List[dict[str, Any]]],
    last_user_text: str,
    latest_message_info: Optional[dict],
    audio_url: Optional[str],
    request: ChatCompletionRequest,
    source_imate_id: Optional[str],
    user_message_id: Optional[int] = None,
    subscription_actions: Optional[List[BizAction]] = None,
    client_local_id: Optional[str] = None,
) -> dict:
    """构建聊天响应数据"""
    message = {"role": "assistant", "content": response_text_content}
    if response_content_parts is not None and len(response_content_parts) > 0:
        message["content_parts"] = response_content_parts
    if subscription_actions is None or len(subscription_actions) == 0:
        # 无实际效果数据，仅用于测试 Kotlin 客户端代码接收到了这个字段（Kotlin 客户端类型代码定义正确）。
        subscription_actions = [
            BizAction(action_type=ActionType.NONE, message=""),
        ]

    if latest_message_info:
        message["id"] = latest_message_info["id"]
        message["meta_data"] = latest_message_info["meta_data"]
        message["timestamp"] = latest_message_info["timestamp"]
        message["audio_url"] = latest_message_info["audio_url"] or audio_url
    elif audio_url:
        message["audio_url"] = audio_url

    if message.get("audio_url"):
        logger.debug(f"响应包含语音URL: {message['audio_url']}")

    response = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "user_message_id": user_message_id,
        "business_actions": [a.model_dump() for a in subscription_actions],
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": len(last_user_text.split()),
            "completion_tokens": len(response_text_content.split()),
            "total_tokens": len(last_user_text.split())
            + len(response_text_content.split()),
        },
    }
    if source_imate_id is not None:
        response["source_imate_id"] = source_imate_id
    if client_local_id:
        response["local_id"] = client_local_id
    return response


def _should_trigger_premium_preview(
    *,
    is_subscribed: bool,
    next_chat_count: int,
) -> bool:
    if is_subscribed:
        return False
    if (
        not global_config_loaded_from_config_yaml.agent.enable_free_user_premium_preview
    ):
        return False
    preview_every = (
        global_config_loaded_from_config_yaml.agent.free_user_premium_preview_every_n_messages
    )
    if preview_every <= 0:
        return False
    return next_chat_count % preview_every == 0


def _truncate_premium_preview_content(content: str) -> str:
    max_chars = (
        global_config_loaded_from_config_yaml.agent.free_user_premium_preview_max_chars
    )
    if max_chars <= 0 or len(content) <= max_chars:
        return content
    return content[:max_chars].rstrip() + "..."


def _build_premium_preview_choice(preview_content: str) -> dict:
    return {
        "role": "assistant",
        "type": "premium_preview",
        "content": (
            "Premium-only preview:\n"
            f"{preview_content}\n\n"
            "Subscribe to Premium to unlock this quality in every chat."
        ),
        "meta_data": dump_chat_ws_companion_wire_meta(
            ChatWsCompanionWireMetaData(
                premium_only=True,
                source="free_user_premium_preview",
            )
        ),
    }


def _build_premium_subscription_action(next_chat_count: int) -> BizAction:
    msg_idx = next_chat_count % len(GENERAL_SUBSCRIPTION_POPUP_MESSAGES)
    return BizAction(
        action_type=ActionType.SUBSCRIPTION_POPUP,
        message=GENERAL_SUBSCRIPTION_POPUP_MESSAGES[msg_idx],
    )


async def _try_generate_premium_preview_choice(
    *,
    agent,
    current_user: UserSchema,
    session_id: str,
    last_user_text: str,
    chat_settings: ChatSettings,
    user_time_context: Optional[dict],
) -> Optional[dict]:
    premium_settings = SimpleNamespace(
        premium_mode=True,
        style_prompt=chat_settings.style_prompt,
        voice_enabled=False,
    )
    premium_model_override = select_chat_model(
        user=current_user, is_subscribed=True
    )
    premium_preview_prompt = (
        "Generate one short premium-only sample reply for the user's latest message. "
        "Make it deeper, warmer, and more personalized than free mode. "
        "Return only the reply text in one paragraph (max 80 words).\n"
        f"User latest message: {last_user_text or '[No plain text content provided]'}"
    )
    gen_result = await agent.generate_message_without_user_save(
        user_id=current_user.id,
        session_id=session_id,
        messages=[HumanMessage(content=premium_preview_prompt)],
        chat_settings=premium_settings,
        user_time_context=user_time_context,
        model_override=premium_model_override.id_on_provider,
        is_subscribed=True,
    )
    if not gen_result:
        return None
    preview_content, _trace_id = (
        gen_result if isinstance(gen_result, tuple) else (gen_result, None)
    )
    preview_content = _truncate_premium_preview_content(
        preview_content.strip() if preview_content else ""
    )
    if not preview_content:
        return None
    return _build_premium_preview_choice(preview_content)


def _companion_rejects_multimodal_user_turn(
    last_user_message: ChatMessage,
) -> bool:
    return last_user_message.has_image_content_part()


def _companion_turn_voice_ctx(
    *,
    chat_settings: Any,
    agent_data: dict[str, Any],
    language: str,
) -> dict[str, object]:
    """Voice/TTS resolution for companion foreground and tool_background turns."""
    return {
        "chat_voice_id": chat_settings.voice_id,
        "agent_voice_id": agent_data.get("voice_id"),
        "agent_gender": agent_data.get("gender"),
        "agent_settings": agent_data.get("settings"),
        "language": language,
    }




async def _persist_companion_user_message_for_bg(
    *,
    session_id: str,
    last_user_message: ChatMessage,
    effective_local_id: Optional[str],
    implicit_greeting_turn: bool,
) -> Optional[int]:
    """Write user message into ``chat_history`` for one companion turn (success or bg-survives-fg-fail).

    After dual-LLM foreground-before-background dispatch, ``bg-survives-fg-fail`` should not occur;
    this helper remains as a defensive path for any future or alternate companion wiring.

    Mirrors the success-path branching:
    - ``implicit_greeting_turn`` -> no row written; returns ``None`` (protocol skips user history).
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
                ChatWsCompanionWireMetaData(local_id=effective_local_id)
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
    _fg_script = (companion_turn.voice_message_script or "").strip()
    is_voice = None
    voice_message_script = None
    if str(companion_turn.reply_modality or "") == "voice_message":
        is_voice = True
        if _fg_script:
            voice_message_script = _fg_script
    sp = companion_turn.significance_perception
    significance = sp if isinstance(sp, dict) and sp else None
    meta = ChatWsCompanionWireMetaData(
        source=companion_turn.assistant_source,
        reply_modality=companion_turn.reply_modality,
        inner_tick_activity=companion_turn.inner_tick_activity,
        is_voice=is_voice,
        voice_message_script=voice_message_script,
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


async def _agent_status_line_for_chat_header(
    db: AsyncSession, agent_id: str
) -> Optional[str]:
    r = await db.execute(
        select(Agent.status_line).where(
            Agent.id == agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    raw = r.scalar_one_or_none()
    text = (raw or "").strip()
    return text if text else None


async def _agent_chat_completions_impl(
    *,
    db: AsyncSession,
    agent_id: str,
    request: ChatCompletionRequest,
    current_user: UserSchema,
    app_version_code: Optional[int],
    subscription_svc: SubscriptionService,
    voice_svc: VoiceService,
    chat_route: Literal["http", "websocket"],
    companion_background_sink: Callable[[ToolOutputEvent], None] | None = None,
    companion_ws_foreground_pending: dict[str, dict[str, Any]] | None = None,
    companion_ws_inner_tick_ctx: dict[str, Any] | None = None,
    implicit_greeting_turn: bool = False,
) -> Union[APIResponse[dict], dict]:
    # TODO(cleanup-ws-http-chat-impl): WS callers use _agent_chat_ws_completions_impl;
    # remove chat_route, WS-only params, and chat_route=="websocket" branches here.
    try:
        request_handling_timer = Timer("请求处理")
        logger.debug(
            f"聊天请求 - agent_id={agent_id}, user_id={current_user.id}, messages={len(request.messages)}"
        )

        # 获取或创建与该Agent的唯一会话
        with log_time(
            f"获取或创建聊天会话: user_id={current_user.id}, agent_id={agent_id}"
        ):
            chat = await chat_service.get_or_create_chat_by_agent(
                db=db, user_id=current_user.id, agent_id=agent_id
            )

        # 验证返回的chat中的agent_id是否与传入的一致
        if chat.agent_id != agent_id:
            logger.error(
                f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: expected={agent_id}, actual={chat.agent_id}",
            )

        # 获取最后一条用户消息
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")

        last_user_message = user_messages[-1].to_model_content()
        last_user_chat_message = user_messages[-1]
        last_user_text = last_user_chat_message.extract_text_content()
        messages = [HumanMessage(content=last_user_message)]
        logger.debug(
            f"聊天请求最后一条用户消息: has_multimodal={isinstance(last_user_message, list)}, text_length={len(last_user_text)}"
        )
        user_time_context = (
            request.user_time_context.model_dump(exclude_none=True)
            if request.user_time_context
            else None
        )
        if user_time_context == {}:
            user_time_context = None

        effective_local_id = (
            request.local_id or request.message_id or ""
        ).strip() or None

        implicit_greeting_ws = (
            chat_route == "websocket" and implicit_greeting_turn
        )
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

        # 使用高性能的聊天专用Agent获取方法
        with log_time(f"查询 Agent 数据: {chat.agent_id}"):
            agent_data = await agent_service.get_agent_for_chat(
                db, agent_id=chat.agent_id
            )

        if not agent_data:
            logger.error(f"Agent数据未找到: {chat.agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")

        with log_time(f"获取 Agent 实例: {chat.agent_id}"):
            agent = await agent_manager.get_agent(agent_data)

        session_id = generate_session_id(str(chat.id))

        with log_time(f"订阅检查: user_id={current_user.id}"):
            is_allowed, used_count, daily_limit = (
                await subscription_svc.check_chat_limit(db, current_user)
            )

        if not is_allowed:
            return await _handle_subscription_limit_error(
                session_id,
                last_user_message,
                current_user,
                used_count,
                daily_limit,
                client_local_id=effective_local_id,
            )

        # 获取聊天设置和AI回复
        use_companion = False
        companion_reply_modality = "text"
        companion_voice_script = ""
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
                # TODO(cleanup-ws-http-chat-impl): dead for WS callers; HTTP-only -> False, drop companion block.
                use_companion = chat_route == "websocket"
                _agent_cfg = global_config_loaded_from_config_yaml.agent
                _chat_llm_base = (
                    _agent_cfg.chat_llm_base_url or _agent_cfg.base_url or ""
                ).strip() or "https://openrouter.ai/api/v1"
                logger.debug(
                    "chat_turn route={} companion={} user={} chat_id={} agent_id={} model={} subscribed={} chat_llm_api_base={}",
                    chat_route,
                    use_companion,
                    current_user.id,
                    chat.id,
                    agent_id,
                    model_override,
                    is_subscribed,
                    _chat_llm_base,
                )
                if (
                    use_companion
                    and (not implicit_greeting_ws)
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
                    ai_message_id = (
                        await chat_history_service.add_ai_message_sync_async(
                            session_id,
                            response_text_content,
                            agent_id=chat.agent_id,
                            meta_data=dump_chat_ws_companion_wire_meta(
                                ChatWsCompanionWireMetaData.model_validate(
                                    phone_meta
                                )
                            ),
                        )
                    )
                    if (
                        companion_ws_inner_tick_ctx is not None
                        and chat_route == "websocket"
                    ):
                        apply_companion_ws_inner_tick_coords(
                            companion_ws_inner_tick_ctx,
                            user_id=current_user.id,
                            agent_id=agent_id,
                            chat_id=chat.id,
                        )
                    _ = companion_user_row_id
                # TODO(cleanup-ws-http-chat-impl): companion block WS-only; delete when HTTP-only.
                elif use_companion:
                    companion_preset_uid: str | None = None
                    if (
                        chat_route == "websocket"
                        and companion_ws_foreground_pending is not None
                    ):
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
                            "voice_enabled": chat_settings.voice_enabled,
                            "chat_voice_id": chat_settings.voice_id,
                            "agent_voice_id": agent_data.get("voice_id"),
                            "agent_gender": agent_data.get("gender"),
                            "agent_settings": agent_data.get("settings"),
                            "language": request.language,
                        }
                    companion_voice_ctx = _companion_turn_voice_ctx(
                        chat_settings=chat_settings,
                        agent_data=agent_data,
                        language=request.language,
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
                                voice_ctx=companion_voice_ctx,
                            )
                        else:
                            companion_turn = await companion_chat_service.run_companion_user_chat_turn_for_api(
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
                                voice_ctx=companion_voice_ctx,
                            )
                        companion_reply_modality = companion_turn.reply_modality
                        companion_voice_script = (
                            companion_turn.voice_message_script or ""
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
                        # TODO(companion-dual-envelope-reasoning-channel): Root cause is usually upstream:
                        # structured chat completion has empty ``message.content`` while LangSmith shows
                        # output under ``reasoning``. Compare trace vs ``deepseek-v4-pro`` vs ``v3.2``.
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
                    if (
                        companion_ws_inner_tick_ctx is not None
                        and chat_route == "websocket"
                    ):
                        apply_companion_ws_inner_tick_coords(
                            companion_ws_inner_tick_ctx,
                            user_id=current_user.id,
                            agent_id=agent_id,
                            chat_id=chat.id,
                        )
                else:
                    chat_result = await agent.chat(
                        user_id=current_user.id,
                        session_id=session_id,
                        messages=messages,
                        chat_settings=chat_settings,
                        user_time_context=user_time_context,
                        model_override=model_override.id_on_provider,
                        is_subscribed=is_subscribed,
                        client_local_message_id=effective_local_id,
                    )
                    response_content, ai_message_id = (
                        (chat_result[0], chat_result[1])
                        if isinstance(chat_result, tuple)
                        else (chat_result, None)
                    )

                    if response_content is None:
                        logger.error(
                            f"Chat 返回无内容 - agent_id={agent_id}, user_id={current_user.id}"
                        )
                        raise HTTPException(
                            status_code=500, detail="Chat returned no content"
                        )
                    (
                        response_text_content,
                        response_content_parts,
                    ) = _normalize_chat_response_content(response_content)

            response_preview = (
                response_text_content[:100]
                if response_text_content
                else f"[multimodal parts={len(response_content_parts or [])}]"
            )
            logger.debug(f"Agent聊天响应成功: {response_preview}...")
            subscription_actions = None
            premium_preview_choice = None
            next_chat_count = used_count + 1
            if not use_companion and _should_trigger_premium_preview(
                is_subscribed=is_subscribed,
                next_chat_count=next_chat_count,
            ):
                try:
                    with log_time(
                        f"生成付费预览内容: user_id={current_user.id}, chat_count={next_chat_count}"
                    ):
                        premium_preview_choice = (
                            await _try_generate_premium_preview_choice(
                                agent=agent,
                                current_user=current_user,
                                session_id=session_id,
                                last_user_text=last_user_text,
                                chat_settings=chat_settings,
                                user_time_context=user_time_context,
                            )
                        )
                    if premium_preview_choice is not None:
                        subscription_actions = [
                            _build_premium_subscription_action(next_chat_count)
                        ]
                except Exception as e:
                    logger.warning(f"生成付费预览失败，已跳过: {str(e)}")

            # 用户发送消息后，标记该用户的所有未读推送为已读
            try:
                read_count = await mark_user_push_notifications_as_read(
                    db, current_user.id
                )
                if read_count > 0:
                    logger.debug(
                        f"标记用户推送为已读: user_id={current_user.id}, count={read_count}"
                    )
            except Exception as e:
                # 标记已读失败不应该影响聊天流程，只记录日志
                logger.warning(
                    f"标记用户推送为已读失败: user_id={current_user.id}, error={str(e)}"
                )

        except HTTPException:
            raise
        except CompanionLLMInferenceBackendError:
            raise
        except Exception as e:
            logger.error(f"Agent聊天处理失败: {str(e)}")
            raise

        audio_url = None
        audio_duration = None
        try:
            audio_url, audio_duration = await synthesize_chat_assistant_audio(
                db=db,
                session_id=session_id,
                ai_message_id=ai_message_id,
                voice_enabled=chat_settings.voice_enabled,
                chat_voice_id=chat_settings.voice_id,
                agent_voice_id=agent_data.get("voice_id"),
                agent_gender=agent_data.get("gender"),
                agent_settings=agent_data.get("settings"),
                language=request.language,
                current_user=current_user,
                voice_svc=voice_svc,
                response_text_content=response_text_content,
                use_companion=use_companion,
                companion_reply_modality=companion_reply_modality,
                companion_voice_script=companion_voice_script,
            )
        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")

        # 记录聊天使用情况
        try:
            with log_time(f"记录使用情况: user_id={current_user.id}"):
                usage_extra: dict[str, Any] = {
                    "agent_id": agent_id,
                    "message_length": len(last_user_text),
                }
                if implicit_greeting_ws:
                    usage_extra["implicit_user_signed_on"] = True
                await subscription_svc.record_usage(
                    db,
                    current_user.id,
                    "chat",
                    1,
                    extra_data=usage_extra,
                )
            logger.debug("聊天使用情况记录成功")
        except Exception as e:
            logger.warning(f"记录聊天使用情况失败: {str(e)}")

        surprise_snap_message_id = None
        try:
            surprise_snap_message_id = await try_trigger_surprise_snap(
                db, session_id, current_user.id, agent_id
            )
        except Exception as e:
            logger.warning(f"Surprise Snap 触发失败: {e}")

        # 获取 AI 消息完整信息：插入时已拿到 message id 则按 id 查，否则查最新一条
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

        # 仅当客户端提供版本且满足最低要求时按需投递；未传版本或旧版不投递，delivery_at 保持 null
        delivered_prompts = []
        if is_festival_memory_enabled(app_version_code):
            try:
                with log_time(
                    f"投递节日记忆提示: user_id={current_user.id}, agent_id={agent_id}"
                ):
                    delivered_prompts = (
                        await deliver_festival_memories_for_user_agent(
                            db, current_user.id, agent_id
                        )
                    )
            except Exception as e:
                await db.rollback()
                logger.warning(f"投递节日记忆提示失败: {e}")
                delivered_prompts = []

        delivered_daily_prompts = []
        if is_daily_memory_enabled(app_version_code):
            try:
                with log_time(
                    f"投递日常记忆提示: user_id={current_user.id}, agent_id={agent_id}"
                ):
                    delivered_daily_prompts = (
                        await deliver_daily_memories_for_user_agent(
                            db, current_user.id, agent_id
                        )
                    )
            except Exception as e:
                await db.rollback()
                logger.warning(f"投递日常记忆提示失败: {e}")
                delivered_daily_prompts = []

        # 构建响应
        data = _build_chat_response(
            response_text_content,
            response_content_parts,
            last_user_text,
            latest_message_info,
            audio_url,
            request,
            source_imate_id=request.target_imate_id,
            user_message_id=user_message_id,
            subscription_actions=subscription_actions,
            client_local_id=effective_local_id,
        )

        if premium_preview_choice is not None:
            idx = len(data["choices"])
            data["choices"].append(
                {
                    "index": idx,
                    "message": premium_preview_choice,
                    "finish_reason": "stop",
                }
            )

        # 若有本次投递的节日提醒，追加到 choices（仅当 is_festival_memory_enabled 时才会投递，故此处不必再判版本）
        if delivered_prompts:
            msg_ids = [
                item["message_id"]
                for item in delivered_prompts
                if item.get("message_id") is not None
            ]
            infos_map = await chat_history_service.get_ai_message_infos_by_ids(
                db, msg_ids
            )
            for item in delivered_prompts:
                msg_id = item.get("message_id")
                info = infos_map.get(msg_id) if msg_id is not None else None
                message = _build_festival_prompt_choice_message(item, info)
                idx = len(data["choices"])
                data["choices"].append(
                    {"index": idx, "message": message, "finish_reason": "stop"}
                )

        if delivered_daily_prompts:
            msg_ids = [
                item["message_id"]
                for item in delivered_daily_prompts
                if item.get("message_id") is not None
            ]
            infos_map = await chat_history_service.get_ai_message_infos_by_ids(
                db, msg_ids
            )
            for item in delivered_daily_prompts:
                msg_id = item.get("message_id")
                info = infos_map.get(msg_id) if msg_id is not None else None
                message = _build_daily_prompt_choice_message(item, info)
                idx = len(data["choices"])
                data["choices"].append(
                    {"index": idx, "message": message, "finish_reason": "stop"}
                )

        # 若本次触发了 Surprise Snap，追加一条 choice 与消息列表结构一致
        if surprise_snap_message_id is not None:
            info = await chat_history_service.get_surprise_snap_message_display_info(
                db, surprise_snap_message_id
            )
            if info is not None:
                unlocked_ids = await get_unlocked_surprise_snap_message_ids(
                    db, current_user.id
                )
                message = _build_surprise_snap_choice_message(
                    info,
                    unlocked_message_ids=unlocked_ids,
                )
                idx = len(data["choices"])
                data["choices"].append(
                    {"index": idx, "message": message, "finish_reason": "stop"}
                )

        timing_message = request_handling_timer.stop()
        logger.debug(f"聊天请求完成: agent_id={agent_id}, {timing_message}")

        payload = APIResponse.success(data=data)
        # TODO(cleanup-ws-http-chat-impl): WS dict return dead; HTTP keeps APIResponse only.
        if chat_route == "websocket":
            sl = await _agent_status_line_for_chat_header(db, agent_id)
            out = payload.model_dump(exclude_none=True)
            out["status_line"] = sl
            return out
        return payload

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


@router.post(
    "/completions/{agent_id}",
    response_model=APIResponse[dict],
    summary="返回与指定 Agent 聊天的下一条消息",
    description="可以处理包括图片在内的各种消息类型，媒体类型应该先上传，然后将 URL 作为索引发送到此 API",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
async def agent_chat_completions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ChatCompletionRequest,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
    app_version_code: Optional[int] = Header(None, alias="appVersionCode"),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
    voice_svc: VoiceService = Depends(deps.get_voice_service),
):
    """
    基于Agent ID的OpenAI风格聊天接口；evaluation 可传 X-Assume-User-Id 以该用户身份聊天并加载其历史。
    如果用户还没有和该Agent创建会话，则自动创建
    """
    if (
        global_config_loaded_from_config_yaml.app.api_endpoints.disable_api_v1_chat_completions
    ):
        raise HTTPException(
            status_code=404, detail="API v1 chat completions is disabled"
        )
    if request.stream:
        raise HTTPException(status_code=400, detail="Stream is not supported")

    # TODO(transport): HTTP companion omits companion_background_sink; tool_bg falls through to
    # push_output_event global queue (see tool_background._effective_on_event). Align with WS
    # sink or explicitly document unsupported async tool_bg delivery for this route.
    # TODO(cleanup-ws-http-chat-impl): HTTP uses _agent_chat_completions_impl; WS uses
    # _agent_chat_ws_completions_impl — evolve companion_background_sink on HTTP independently.
    return await _agent_chat_completions_impl(
        db=db,
        agent_id=agent_id,
        request=request,
        current_user=current_user,
        app_version_code=app_version_code,
        subscription_svc=subscription_svc,
        voice_svc=voice_svc,
        chat_route="http",
    )




class ChatImageBizErrorData(BizError):
    description: Optional[str] = None
    suggestion: Optional[str] = None


ChatImageGenerationAPIResponse: TypeAlias = APIResponse[
    Union[
        ChatImageGenerationResponse,
        UsageLimitExceeded,
        ChatImageBizErrorData,
    ]
]


ChatMusicGenerationAPIResponse: TypeAlias = APIResponse[
    Union[
        ChatMusicGenerationResponse,
        UsageLimitExceeded,
    ]
]


@router.post(
    "/images/{agent_id}",
    response_model=ChatImageGenerationAPIResponse,
    summary="基于聊天消息及历史消息和其他相关信息（角色背景、用户 profile 等）生成图片",
    description=(
        "根据Agent角色、聊天历史和用户消息生成图片，并保存到聊天历史中。"
        "注意：路径参数 `agent_id` 仅作为目前的名称，实际应为 `chat_id`。未来如需扩展可直接重命名。"
        "agent id 则代表与该 agent 的*当前*会话的 id"
    ),
)
async def generate_chat_image(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ChatImageGenerationRequest,
    current_user: UserSchema = Depends(deps.get_current_active_user),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
) -> ChatImageGenerationAPIResponse:
    """
    基于聊天上下文生成图片

    流程：
    1. 验证用户和Agent
    2. 获取或创建聊天会话
    3. 检查图片生成限额
    4. 调用图片生成服务
    5. 记录用量
    6. 返回图片信息

    注意：
    - 路径参数 `agent_id` 仅作为目前的名称，实际应为 `chat_id`
    - 本 API 拷贝自 `app/api/v1/endpoints/chats.py::generate_chat_image`（第1170-1325行）
    - 核心逻辑已提取到 `chat_service.generate_chat_image`
    """
    try:
        # 返回值：
        # 1. 成功时返回 ChatImageGenerationResponse
        # 2. 业务限制错误时返回 UsageLimitExceeded 或 BizError
        # 3. 其他错误时返回 HTTPException
        # 1，2 均显示为应用正常返回值、3 为 fastapi 返回值
        result = await chat_service.generate_chat_image(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            message_id=request.message_id,
            subscription_service=subscription_svc,
            history_count=request.history_count,
            model=request.model,
        )

        if isinstance(result, UsageLimitExceeded):
            return APIResponse.error(
                message=result.message, code=result.code, data=result
            )

        if isinstance(result, BizError):
            # 返回业务错误响应，包含额外的错误信息
            return create_business_error_response(
                error_info={
                    "code": result.code,
                    "error_code": result.error_code,
                    "message": result.message,
                },
                extra_data={
                    "code": result.code,
                    "message": result.message,
                    "suggestion": "Please modify your prompt and try again.",
                },
            )

        return APIResponse.success(data=result)

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(
            f"生成聊天图片失败 - Agent ID: {agent_id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate image: {str(e)}"
        )


@router.post(
    "/music/{agent_id}",
    response_model=ChatMusicGenerationAPIResponse,
    summary="基于聊天消息及上下文生成背景音乐",
    description=(
        "根据 Agent 角色设定、聊天历史和目标消息，生成一段可用于当前对话氛围的背景音乐。"
    ),
    tags=[INTY_EVAL_TAG],
)
async def generate_chat_music(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ChatMusicGenerationRequest,
    current_user: UserSchema = Depends(deps.get_current_active_user),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
) -> ChatMusicGenerationAPIResponse:
    """基于聊天上下文生成音乐。"""
    try:
        result = await chat_service.generate_chat_music(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            message_id=request.message_id,
            subscription_service=subscription_svc,
            history_count=request.history_count,
            model=request.model,
        )

        if isinstance(result, UsageLimitExceeded):
            return APIResponse.error(
                message=result.message, code=result.code, data=result
            )

        return APIResponse.success(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"生成聊天音乐失败 - Agent ID: {agent_id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate music: {str(e)}"
        )
