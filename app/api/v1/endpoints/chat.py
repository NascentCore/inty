"""Chat completion and WebSocket endpoints for app conversations.

This module exposes HTTP chat completions plus the persistent chat WebSocket used
by Android clients and companion-agent sessions.
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

from app import models, schemas
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
from app.core.agentic_kernel.companion.heartbeat import (
    HeartbeatConfig,
    PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER,
    next_heartbeat_wait_seconds,
)
from app.core.agentic_kernel.companion.llm_inference_errors import (
    CompanionLLMInferenceBackendError,
)
from app.core.agentic_kernel.companion.image_gate import (
    generated_image_meta_from_index_slice,
)
from app.core.agentic_kernel.companion.models import CompanionTurnResult, InnerTickMode
from app.core.agentic_kernel.companion.tool_background import ToolOutputEvent
from app.core.model_selection import select_chat_model
from app.models.user import AuthType, User
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
    ChatWebSocketRequest,
    ChatWsUserSignedOnFrame,
    CompanionChatTurnMessageType,
    UserTimeContext,
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
from app.services.chat_websocket_session import chat_ws_outbound_pump
from app.services.ws_session_messages import WsOutboundPayload
from app.services.memory_service import (
    deliver_daily_memories_for_user_agent,
    deliver_festival_memories_for_user_agent,
)
from app.db.session import AsyncSessionLocal
from app.services.chat_service import generate_session_id
from app.services.subscription_service import SubscriptionService
from app.services.surprise_snap_service import (
    get_unlocked_surprise_snap_message_ids,
    try_trigger_surprise_snap,
)
from app.services.push_notification_service import mark_user_push_notifications_as_read
from app.services.voice_service import (
    VoiceService,
    get_voice_message_narration_mode_from_agent_settings,
)
from app.utils.openai_client import get_chat_openai_client
from app.utils.timing import Timer, log_time

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


def _chat_ws_error_payload_from_http_exception(
    exc: HTTPException, *, agent_id: str
) -> dict[str, Any]:
    detail = exc.detail
    message = detail if isinstance(detail, str) else str(detail)
    payload: dict[str, Any] = {
        "code": exc.status_code,
        "message": message,
        "data": None,
        "agent_id": agent_id,
    }
    ws_extra = getattr(exc, "ws_extra", None)
    if isinstance(ws_extra, dict):
        payload.update(ws_extra)
    return payload


# WebSocket: one AsyncSession is bound for the whole connection (Depends(get_async_db)).
# Handlers must not pass that session into asyncio.to_thread or other threads; open a new
# session inside the worker if agentic work runs off the event loop.


def _chat_ws_idle_timeout_seconds() -> float:
    return float(
        global_config_loaded_from_config_yaml.app.features.chat_ws_idle_timeout_seconds
    )


async def _shutdown_chat_ws_outbound_pump(pump_task: asyncio.Task) -> None:
    """Join ``chat_ws_outbound_pump``; distinguish normal cancellation from send failures."""
    if not pump_task.done():
        pump_task.cancel()
    try:
        await pump_task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception(
            "chat_ws_outbound_pump failed (e.g. WebSocket send_json); "
            "distinct from normal CancelledError teardown"
        )


async def _verify_ws_simple_llm_reply(
    *,
    agent_row: dict[str, Any],
    user_text: str,
    model_name: str,
) -> str:
    """
    Single chat-completions call (system + user only). No Agent instance, no history, no tools.
    Used by ``/ws/verify`` only.
    """
    name = (agent_row.get("name") or "Assistant").strip() or "Assistant"
    snippet = (agent_row.get("personality") or agent_row.get("intro") or "").strip()
    if snippet:
        system = f"You are {name}. Character notes: {snippet[:1200]}"
    else:
        system = f"You are {name}. Reply concisely in the same language as the user's message."

    client = get_chat_openai_client()

    def _sync_call() -> str:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            max_tokens=2048,
            temperature=0.7,
        )
        if not resp.choices:
            return ""
        return (resp.choices[0].message.content or "").strip()

    return await asyncio.to_thread(_sync_call)


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


async def _handle_chat_websocket_control_json(
    websocket: WebSocket,
    data: Any,
    tc_box: list[Optional[dict]],
) -> bool:
    """
    Handle ping / client_context on chat WebSockets. tc_box is a length-1 list holding the
    session's last validated time_context dict (or None). Returns True if the frame was consumed.

    **Transport vs logical channel:** control frames (ping/pong, client_context_ack) are answered
    directly on the WebSocket. Proactive heartbeat coords are set by ``user_signed_on`` (see
    ``_try_handle_ws_user_signed_on_frame``) and refreshed on each successful WebSocket companion
    chat turn (``_agent_chat_completions_impl``). They are independent of the connection-level outbound queue used
    for assistant/business JSON. Intentionally so: the WebSocket sits *below* the repl/client
    logical session with the agent; control traffic only confirms link/time-context at the wire layer,
    not the agent dialogue FIFO (which is serialized via ``outbound_queue`` + pump).
    """
    if not isinstance(data, dict):
        return False
    msg_type = data.get("type")
    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})
        return True
    if msg_type != "client_context":
        return False
    tc_raw = data.get("time_context")
    if not isinstance(tc_raw, dict):
        await websocket.send_json({"type": "client_context_ack", "ok": False})
        return True
    try:
        validated = UserTimeContext.model_validate(tc_raw)
        dumped = validated.model_dump(exclude_none=True)
        tc_box[0] = dumped if dumped else None
        await websocket.send_json({"type": "client_context_ack", "ok": True})
    except ValidationError:
        await websocket.send_json({"type": "client_context_ack", "ok": False})
    return True


async def _try_handle_ws_user_signed_on_frame(
    websocket: WebSocket,
    data: Any,
    *,
    db: AsyncSession,
    current_user: schemas.User,
    companion_hb_ctx: dict[str, Any] | None,
) -> bool:
    """
    Consume ``{"type":"user_signed_on","agent_id":...}``.

    Product intent: companion should mimic a person who sees the user come online and can
    greet proactively when the client also sends ``messageType: IMPLICIT_USER_SIGNED_ON``
    (trigger copy in ``/app/core/agentic_kernel/companion/implicit_signal_messages.py``); this frame is the
    client-side online signal. It also arms proactive heartbeat coords before the first chat
    frame; legacy clients that omit it still get coords after any successful companion turn.

    ``/ws/verify`` passes ``companion_hb_ctx=None`` and receives ``ok: false`` (not supported).
    """
    if not isinstance(data, dict) or data.get("type") != "user_signed_on":
        return False
    if companion_hb_ctx is None:
        await websocket.send_json(
            {
                "type": "user_signed_on_ack",
                "ok": False,
                "reason": "not_supported",
            }
        )
        return True
    feats = global_config_loaded_from_config_yaml.app.features
    if not feats.companion_ws_proactive_heartbeat_enabled:
        await websocket.send_json(
            {
                "type": "user_signed_on_ack",
                "ok": False,
                "reason": "proactive_heartbeat_disabled",
            }
        )
        return True
    try:
        frame = ChatWsUserSignedOnFrame.model_validate(data)
    except ValidationError:
        await websocket.send_json(
            {
                "type": "user_signed_on_ack",
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
                    "type": "user_signed_on_ack",
                    "ok": False,
                    "reason": "agent_mismatch",
                }
            )
            return True
        _companion_ws_store_hb_coords(
            companion_hb_ctx,
            user_id=current_user.id,
            agent_id=agent_id,
            chat_id=chat.id,
        )
        await websocket.send_json({"type": "user_signed_on_ack", "ok": True})
        recv_msg_uuid = (frame.message_id or "").strip()
        logger.info(
            "chat_ws user_signed_on armed proactive hb user={} agent={} chat_id={} "
            "received_message_uuid={}",
            current_user.id,
            agent_id,
            chat.id,
            recv_msg_uuid or "-",
        )
    except Exception:
        logger.exception("chat_ws user_signed_on failed agent_id={}", agent_id)
        await websocket.send_json(
            {"type": "user_signed_on_ack", "ok": False, "reason": "server_error"}
        )
    return True


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
) -> schemas.User:
    """
    Evaluation: superuser may pass assume_user_id query (same semantics as live_chat WS).
    Matches HTTP X-Assume-User-Id for chat so eval WebSocket hits the same code path as production /ws.
    """
    operator_schema = schemas.User.model_validate(operator, from_attributes=True)
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
        return schemas.User.model_validate(assumed, from_attributes=True)
    logger.warning(
        "chat WebSocket assume_user_id not found or deleted: {}", assume_user_id
    )
    return operator_schema


async def _handle_subscription_limit_error(
    session_id: str,
    last_user_message: str | List[dict[str, Any]],
    current_user: schemas.User,
    used_count: int,
    daily_limit: int,
    client_local_id: Optional[str] = None,
) -> schemas.APIResponse:
    """处理订阅限制错误"""
    try:
        meta = {"localId": client_local_id} if client_local_id else None
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


def _build_festival_prompt_choice_message(item: dict, info: Optional[dict]) -> dict:
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


def _build_daily_prompt_choice_message(item: dict, info: Optional[dict]) -> dict:
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
    if not global_config_loaded_from_config_yaml.agent.enable_free_user_premium_preview:
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
        "meta_data": {
            "premium_only": True,
            "source": "free_user_premium_preview",
        },
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
    current_user: schemas.User,
    session_id: str,
    last_user_text: str,
    chat_settings: models.ChatSettings,
    user_time_context: Optional[dict],
) -> Optional[dict]:
    premium_settings = SimpleNamespace(
        premium_mode=True,
        style_prompt=chat_settings.style_prompt,
        voice_enabled=False,
    )
    premium_model_override = select_chat_model(user=current_user, is_subscribed=True)
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
        model_override=premium_model_override,
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


def _companion_rejects_multimodal_user_turn(last_user_message: ChatMessage) -> bool:
    return last_user_message.has_image_content_part()


def _require_websocket_companion_message_id_uuid(request: ChatCompletionRequest) -> str:
    """WebSocket companion turns require a client ``message_id`` that parses as UUID."""
    try:
        return normalize_websocket_companion_message_id_uuid(request.message_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    meta_data = {
        "source": "tool_bg",
        "trace_id": ev.trace_id,
        "reply_to_user_msg_uuid": ev.user_msg_uuid,
        "tool_bg_output_to_user": ev.output_to_user,
        "tool_bg_generation_deliver": ev.generation_deliver,
    }
    if ev.langsmith_trace_id:
        meta_data["langsmith_trace_id"] = ev.langsmith_trace_id
    if ev.langsmith_run_id:
        meta_data["langsmith_run_id"] = ev.langsmith_run_id
    gi = generated_image_meta_from_index_slice(ev.workspace, ev.image_asset_baseline)
    if gi:
        meta_data["generated_image"] = gi
    ai_message_id = await chat_history_service.add_ai_message_sync_async(
        session_id,
        ev.text,
        agent_id=agent_id,
        meta_data=meta_data,
    )
    latest_message_info = None
    try:
        if ai_message_id is not None:
            latest_message_info = await chat_history_service.get_ai_message_info_by_id(
                db, ai_message_id
            )
    except Exception as e:
        logger.warning(f"tool_bg get_ai_message_info_by_id failed: {e}")
    user_message_id = foreground_user_message_id
    if user_message_id is None:
        try:
            user_message_id = await chat_history_service.get_latest_user_message_id(
                db, session_id
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
    payload = schemas.APIResponse.success(data=data)
    out = payload.model_dump(exclude_none=True)
    out["agent_id"] = agent_id
    out["status_line"] = await _agent_status_line_for_chat_header(db, agent_id)
    return out


def _companion_ws_store_hb_coords(
    hb_ctx: dict[str, Any],
    *,
    user_id: Any,
    agent_id: str,
    chat_id: Any,
) -> None:
    """Replace in-connection proactive-heartbeat workspace coordinates."""
    hb_ctx.clear()
    hb_ctx.update({"user_id": user_id, "agent_id": agent_id, "chat_id": chat_id})


def _companion_ws_hb_coords_snapshot(hb_ctx: dict[str, Any]) -> dict[str, Any] | None:
    hb_uid = str(hb_ctx.get("user_id") or "").strip()
    aid = str(hb_ctx.get("agent_id") or "").strip()
    cid = hb_ctx.get("chat_id")
    if not hb_uid or not aid or cid is None:
        return None
    return {"user_id": hb_uid, "agent_id": aid, "chat_id": cid}


def _companion_ai_meta_from_turn_result(
    companion_turn: CompanionTurnResult,
) -> dict[str, Any]:
    """Build assistant ``meta_data`` for chat_history / WS from one companion kernel turn."""
    companion_ai_meta: dict[str, Any] = {
        "source": companion_turn.assistant_source,
    }
    if companion_turn.trace_id:
        companion_ai_meta["trace_id"] = companion_turn.trace_id
    if companion_turn.user_msg_uuid:
        companion_ai_meta["user_msg_uuid"] = companion_turn.user_msg_uuid
    if companion_turn.langsmith_trace_id:
        companion_ai_meta["langsmith_trace_id"] = companion_turn.langsmith_trace_id
    if companion_turn.langsmith_run_id:
        companion_ai_meta["langsmith_run_id"] = companion_turn.langsmith_run_id
    sp = companion_turn.significance_perception
    if isinstance(sp, dict) and sp:
        companion_ai_meta["significance_perception"] = sp
    return companion_ai_meta


async def _try_fire_companion_ws_proactive_heartbeat(
    *,
    outbound_queue: asyncio.Queue,
    ctx: dict[str, Any],
    subscription_svc: SubscriptionService,
    companion_turn_lock: asyncio.Lock,
) -> None:
    """If companion transcript says proactive heartbeat is due, run one turn and queue WS payload."""
    user_id = str(ctx.get("user_id") or "").strip()
    agent_id = str(ctx.get("agent_id") or "").strip()
    chat_id_raw = ctx.get("chat_id")
    if not user_id or not agent_id or chat_id_raw is None:
        return

    async with AsyncSessionLocal() as pre_db:
        r_user = await pre_db.execute(select(User).where(User.id == user_id))
        current_user = r_user.scalar_one_or_none()
        if current_user is None:
            return

        chat = await chat_service.get_or_create_chat_by_agent(
            db=pre_db, user_id=user_id, agent_id=agent_id
        )
        if str(chat.id) != str(chat_id_raw):
            logger.debug(
                "companion_ws_proactive_hb chat_id mismatch ctx={} db_chat_id={}",
                chat_id_raw,
                chat.id,
            )
            return

        subscription = await subscription_svc.get_user_current_subscription(
            pre_db, user_id
        )
        is_subscribed = bool(subscription)
        model_override = select_chat_model(
            user=current_user, is_subscribed=is_subscribed
        )

        ws_path = companion_chat_service.companion_workspace_path_if_ready(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat.id,
            resolved_chat_model_id=model_override,
        )
        if ws_path is None:
            return

        remain = next_heartbeat_wait_seconds(
            ws_path,
            HeartbeatConfig(enabled=True),
        )
        if remain > 0:
            return

        is_allowed, used_count, daily_limit = await subscription_svc.check_chat_limit(
            pre_db, current_user
        )
        if not is_allowed:
            logger.info(
                "companion_ws_proactive_hb skipped subscription user={} used={} limit={}",
                user_id,
                used_count,
                daily_limit,
            )
            return

        chat_row_id = chat.id
        chat_row_agent_id = chat.agent_id
        session_id = generate_session_id(str(chat_row_id))
        preset_uid = str(uuid.uuid4())

    async with companion_turn_lock:
        companion_turn = await companion_chat_service.run_companion_chat_turn_for_api(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_row_id,
            user_text=PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER,
            resolved_chat_model_id=model_override,
            defer_memory_update=True,
            session_id=session_id,
            background_output_sink=None,
            preset_user_msg_uuid=preset_uid,
            inner_tick_turn=True,
            inner_tick_mode=InnerTickMode.PROACTIVE_CHAT,
        )

        companion_reply = companion_turn.assistant_text
        if companion_reply is None or not str(companion_reply).strip():
            logger.warning(
                "companion_ws_proactive_hb empty reply user={} agent={}",
                user_id,
                agent_id,
            )
            return

        user_meta = {
            "companion_proactive_heartbeat": True,
            "inner_tick": True,
            "heartbeat": True,
        }
        await chat_history_service.add_user_message_async(
            session_id,
            PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER,
            meta_data=user_meta,
        )

        companion_ai_meta = _companion_ai_meta_from_turn_result(companion_turn)

        ai_message_id = await chat_history_service.add_ai_message_sync_async(
            session_id,
            companion_reply,
            agent_id=chat_row_agent_id,
            meta_data=companion_ai_meta,
        )

        async with AsyncSessionLocal() as post_db:
            try:
                await subscription_svc.record_usage(
                    post_db,
                    user_id,
                    "chat",
                    1,
                    extra_data={
                        "agent_id": agent_id,
                        "message_length": 0,
                        "companion_ws_proactive_heartbeat": True,
                    },
                )
            except Exception as e:
                logger.warning(
                    "companion_ws_proactive_hb record_usage failed: {}", str(e)
                )

            stub_request = ChatCompletionRequest(
                messages=[
                    ChatMessage(
                        role="user",
                        content=PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER,
                    )
                ],
                message_id=preset_uid,
            )
            (
                response_text_content,
                response_content_parts,
            ) = _normalize_chat_response_content(companion_reply)

            latest_message_info = None
            try:
                if ai_message_id is not None:
                    latest_message_info = (
                        await chat_history_service.get_ai_message_info_by_id(
                            post_db, ai_message_id
                        )
                    )
                if latest_message_info is None:
                    latest_message_info = (
                        await chat_history_service.get_latest_ai_message_info(
                            post_db, session_id
                        )
                    )
            except Exception as e:
                logger.warning(
                    "companion_ws_proactive_hb latest_message_info failed: {}", e
                )

            user_message_id = None
            try:
                user_message_id = await chat_history_service.get_latest_user_message_id(
                    post_db, session_id
                )
            except Exception as e:
                logger.warning(
                    "companion_ws_proactive_hb get_latest_user_message_id failed: {}",
                    e,
                )

            subscription_actions = [
                BizAction(action_type=ActionType.NONE, message=""),
            ]
            data = _build_chat_response(
                response_text_content,
                response_content_parts,
                PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER,
                latest_message_info,
                None,
                stub_request,
                source_imate_id=None,
                user_message_id=user_message_id,
                subscription_actions=subscription_actions,
                client_local_id=None,
            )
            payload = schemas.APIResponse.success(data=data)
            out = payload.model_dump(exclude_none=True)
            out["agent_id"] = agent_id
            out["status_line"] = await _agent_status_line_for_chat_header(
                post_db, agent_id
            )
            await outbound_queue.put(out)
    logger.info(
        "companion_ws_proactive_hb pushed assistant user={} agent={} chat_id={}",
        user_id,
        agent_id,
        chat_row_id,
    )


async def _agent_status_line_for_chat_header(
    db: AsyncSession, agent_id: str
) -> Optional[str]:
    r = await db.execute(
        select(models.Agent.status_line).where(
            models.Agent.id == agent_id,
            models.Agent.deleted_at.is_(None),
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
    current_user: schemas.User,
    app_version_code: Optional[int],
    subscription_svc: SubscriptionService,
    voice_svc: VoiceService,
    chat_route: Literal["http", "websocket"],
    companion_background_sink: Callable[[ToolOutputEvent], None] | None = None,
    companion_ws_foreground_pending: dict[str, dict[str, Any]] | None = None,
    companion_ws_heartbeat_ctx: dict[str, Any] | None = None,
) -> Union[schemas.APIResponse[dict], dict]:
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
            logger.error(f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}")
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

        if (
            chat_route != "websocket"
            and request.message_type
            == CompanionChatTurnMessageType.IMPLICIT_USER_SIGNED_ON
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "messageType IMPLICIT_USER_SIGNED_ON is only supported on "
                    "WebSocket companion chat"
                ),
            )

        # TODO(implicit-sign-on): If _agent_chat_completions_impl is split into helpers, pass
        # implicit_signed_on_ws explicitly into companion / persistence paths.
        implicit_signed_on_ws = (
            chat_route == "websocket"
            and request.message_type
            == CompanionChatTurnMessageType.IMPLICIT_USER_SIGNED_ON
        )
        if implicit_signed_on_ws and last_user_chat_message.has_image_content_part():
            raise HTTPException(
                status_code=400,
                detail=(
                    "messageType IMPLICIT_USER_SIGNED_ON does not support "
                    "multimodal or image content"
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
        try:
            with log_time(f"获取聊天设置: chat_id={chat.id}"):
                chat_settings = await chat_service.get_or_create_chat_settings(
                    db, chat.id, current_user.id, agent_id
                )

            with log_time(f"AI聊天处理: session_id={session_id}"):
                subscription = await subscription_svc.get_user_current_subscription(
                    db, current_user.id
                )
                is_subscribed = bool(subscription)
                model_override = select_chat_model(
                    user=current_user, is_subscribed=is_subscribed
                )
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
                # TODO(implicit-sign-on): USER_MESSAGE + image-only still uses this generic 400;
                # IMPLICIT_USER_SIGNED_ON + image is rejected earlier with a different message.
                if (
                    use_companion
                    and (not implicit_signed_on_ws)
                    and _companion_rejects_multimodal_user_turn(user_messages[-1])
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Multimodal user turns with images are not supported for the "
                            "companion kernel on WebSocket yet. Send text-only content."
                        ),
                    )
                if use_companion:
                    companion_preset_uid: str | None = None
                    if (
                        chat_route == "websocket"
                        and companion_ws_foreground_pending is not None
                    ):
                        companion_preset_uid = (
                            _require_websocket_companion_message_id_uuid(request)
                        )
                        companion_ws_foreground_pending[companion_preset_uid] = {
                            "session_id": session_id,
                            "agent_id": agent_id,
                            "request": request,
                            "effective_local_id": effective_local_id,
                        }
                    try:
                        companion_implicit_bundle = ImplicitSignalBundle(
                            client_time=request.user_time_context,
                            user_signed_on=(
                                request.message_type
                                == CompanionChatTurnMessageType.IMPLICIT_USER_SIGNED_ON
                            ),
                            server_received_at_utc=datetime.now(timezone.utc),
                        )
                        companion_turn = await companion_chat_service.run_companion_chat_turn_for_api(
                            user_id=current_user.id,
                            agent_id=agent_id,
                            chat_id=chat.id,
                            user_text=last_user_text,
                            resolved_chat_model_id=model_override,
                            defer_memory_update=True,
                            session_id=session_id,
                            background_output_sink=companion_background_sink,
                            preset_user_msg_uuid=companion_preset_uid,
                            implicit_signal_bundle=companion_implicit_bundle,
                        )
                        if (
                            companion_preset_uid is not None
                            and companion_ws_foreground_pending is not None
                            and not companion_turn.tool_background_started
                        ):
                            companion_ws_foreground_pending.pop(
                                companion_preset_uid, None
                            )
                    except Exception:
                        if (
                            companion_preset_uid is not None
                            and companion_ws_foreground_pending is not None
                        ):
                            companion_ws_foreground_pending.pop(
                                companion_preset_uid, None
                            )
                        raise
                    companion_reply = companion_turn.assistant_text
                    companion_ai_meta = _companion_ai_meta_from_turn_result(
                        companion_turn
                    )
                    if implicit_signed_on_ws:
                        companion_ai_meta["messageType"] = (
                            CompanionChatTurnMessageType.IMPLICIT_USER_SIGNED_ON.value
                        )
                        companion_user_row_id = None
                    elif effective_local_id:
                        companion_user_row_id = (
                            await chat_history_service.add_user_message_async(
                                session_id,
                                last_user_message,
                                meta_data={"localId": effective_local_id},
                            )
                        )
                    else:
                        companion_user_row_id = (
                            await chat_history_service.add_user_message_async(
                                session_id, last_user_message
                            )
                        )
                    if (
                        companion_preset_uid is not None
                        and companion_ws_foreground_pending is not None
                        and companion_preset_uid in companion_ws_foreground_pending
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
                    if response_content is None or not str(response_content).strip():
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
                        companion_ws_heartbeat_ctx is not None
                        and chat_route == "websocket"
                    ):
                        _companion_ws_store_hb_coords(
                            companion_ws_heartbeat_ctx,
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
                        model_override=model_override,
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

        # 语音生成逻辑 - 根据chat_settings.voice_enabled决定是否自动播放
        audio_url = None
        audio_duration = None
        try:
            # 语音自动播放逻辑：chat_settings.voice_enabled = true 时自动生成语音
            if chat_settings.voice_enabled and response_text_content.strip():
                selected_chat_voice_id = chat_settings.voice_id
                agent_voice_id = agent_data.get("voice_id")
                # Voice resolution order for MVP:
                # 1) per-chat selected voice_id, 2) agent default voice_id, 3) service fallback.
                resolved_voice_id = selected_chat_voice_id or agent_voice_id
                voice_message_narration_mode = (
                    get_voice_message_narration_mode_from_agent_settings(
                        agent_data.get("settings")
                    )
                )

                with log_time(
                    f"语音生成: voice_id={resolved_voice_id}, text_length={len(response_text_content)}, language={request.language}"
                ):
                    voice_result = await voice_svc.generate_voice(
                        text=response_text_content,
                        voice_id=resolved_voice_id,
                        language=request.language,
                        db=db,
                        agent_gender=agent_data.get("gender"),
                        user=current_user,
                        voice_message_narration_mode=voice_message_narration_mode,
                    )
                if voice_result:
                    audio_url, audio_duration = voice_result
                else:
                    logger.warning(
                        f"用户 {current_user.id} 语音生成失败或达到限制，聊天文本正常返回"
                    )
            elif chat_settings.voice_enabled:
                logger.debug("聊天响应仅包含图片内容，跳过语音生成")
            else:
                logger.debug("语音未启用，跳过语音生成")

        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")
            # 语音生成失败不影响聊天功能

        # 记录聊天使用情况
        try:
            with log_time(f"记录使用情况: user_id={current_user.id}"):
                # TODO(implicit-sign-on): Implicit sign-on still increments chat usage like a normal
                # turn; product may exempt IMPLICIT_USER_SIGNED_ON from limits later.
                usage_extra: dict[str, Any] = {
                    "agent_id": agent_id,
                    "message_length": len(last_user_text),
                }
                if (
                    chat_route == "websocket"
                    and request.message_type
                    == CompanionChatTurnMessageType.IMPLICIT_USER_SIGNED_ON
                ):
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
                user_message_id = await chat_history_service.get_latest_user_message_id(
                    db, session_id
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
                    delivered_prompts = await deliver_festival_memories_for_user_agent(
                        db, current_user.id, agent_id
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

        payload = schemas.APIResponse.success(data=data)
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
    response_model=schemas.APIResponse[dict],
    summary="返回与指定 Agent 聊天的下一条消息",
    description="可以处理包括图片在内的各种消息类型，媒体类型应该先上传，然后将 URL 作为索引发送到此 API",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
async def agent_chat_completions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ChatCompletionRequest,
    current_user: schemas.User = Depends(deps.get_effective_user_for_eval),
    app_version_code: Optional[int] = Header(None, alias="appVersionCode"),
    subscription_svc: SubscriptionService = Depends(deps.get_subscription_service),
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


@router.websocket("/ws")
async def chat_completions_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
    subscription_svc: SubscriptionService = Depends(deps.get_subscription_service),
    voice_svc: VoiceService = Depends(deps.get_voice_service),
):
    await websocket.accept()
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
        if app_version_code_header is not None and app_version_code_header.isdigit()
        else None
    )

    # Business / assistant JSON uses a per-connection queue + pump; control frames bypass the queue
    # (see _handle_chat_websocket_control_json docstring: transport vs logical layer).
    outbound_queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    pump_task = asyncio.create_task(
        chat_ws_outbound_pump(websocket, outbound_queue),
        name="chat_ws_outbound_pump",
    )

    tc_box: list[Optional[dict]] = [None]
    ws_fg_pending: dict[str, dict[str, Any]] = {}
    bg_queue: asyncio.Queue[ToolOutputEvent] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def companion_bg_sink(ev: ToolOutputEvent) -> None:
        loop.call_soon_threadsafe(bg_queue.put_nowait, ev)

    companion_hb_ctx: dict[str, Any] = {}
    companion_turn_lock = asyncio.Lock()
    hb_worker_stop = asyncio.Event()

    async def companion_ws_proactive_hb_worker() -> None:
        while not hb_worker_stop.is_set():
            feats = global_config_loaded_from_config_yaml.app.features
            poll = max(5.0, float(feats.companion_ws_proactive_heartbeat_poll_seconds))
            try:
                await asyncio.wait_for(hb_worker_stop.wait(), timeout=poll)
                break
            except asyncio.TimeoutError:
                pass
            if not feats.companion_ws_proactive_heartbeat_enabled:
                continue
            hb_snapshot: dict[str, Any] | None = None
            async with companion_turn_lock:
                hb_snapshot = _companion_ws_hb_coords_snapshot(companion_hb_ctx)
            if hb_snapshot is None:
                continue
            hb_user_for_log = hb_snapshot["user_id"]
            try:
                await _try_fire_companion_ws_proactive_heartbeat(
                    outbound_queue=outbound_queue,
                    ctx=hb_snapshot,
                    subscription_svc=subscription_svc,
                    companion_turn_lock=companion_turn_lock,
                )
            except Exception:
                logger.exception(
                    "companion_ws_proactive_hb worker failed user_id={}",
                    hb_user_for_log,
                )

    hb_worker_task = asyncio.create_task(
        companion_ws_proactive_hb_worker(),
        name="companion_ws_proactive_heartbeat",
    )

    idle = _chat_ws_idle_timeout_seconds()
    try:
        while True:
            recv_task = asyncio.create_task(
                asyncio.wait_for(websocket.receive_text(), timeout=idle)
            )
            queue_task = asyncio.create_task(bg_queue.get())
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
                    logger.debug(
                        "companion tool_bg receive task ended during queue dispatch: {}",
                        exc,
                    )
                try:
                    ev = queue_task.result()
                except Exception as exc:
                    logger.warning(f"companion tool_bg queue result failed: {exc}")
                    continue
                ctx = ws_fg_pending.pop(ev.user_msg_uuid, None)
                if ctx is None:
                    logger.warning(
                        "companion tool_bg missing foreground ctx user_msg_uuid={}",
                        ev.user_msg_uuid,
                    )
                    continue
                try:
                    async with companion_turn_lock:
                        bg_payload = await _build_companion_tool_background_ws_payload(
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
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = None
            if await _try_handle_ws_user_signed_on_frame(
                websocket,
                data,
                db=db,
                current_user=current_user,
                companion_hb_ctx=companion_hb_ctx,
            ):
                continue
            if await _handle_chat_websocket_control_json(websocket, data, tc_box):
                continue
            if not isinstance(data, dict):
                await outbound_queue.put(
                    {
                        "code": 400,
                        "message": "Chat frame must be a JSON object",
                        "data": None,
                        "agent_id": "",
                    }
                )
                continue
            try:
                websocket_request = ChatWebSocketRequest.model_validate(data)
            except ValidationError as exc:
                await outbound_queue.put(
                    {
                        "code": 422,
                        "message": "Invalid chat WebSocket request",
                        "data": json.loads(exc.json()),
                        "agent_id": str(data.get("agent_id") or ""),
                    }
                )
                continue
            merged_request = _chat_request_with_merged_ws_time_context(
                websocket_request.request,
                tc_box[0],
            )
            try:
                async with companion_turn_lock:
                    response = await _agent_chat_completions_impl(
                        db=db,
                        agent_id=websocket_request.agent_id,
                        request=merged_request,
                        current_user=current_user,
                        app_version_code=app_version_code,
                        subscription_svc=subscription_svc,
                        voice_svc=voice_svc,
                        chat_route="websocket",
                        companion_background_sink=companion_bg_sink,
                        companion_ws_foreground_pending=ws_fg_pending,
                        companion_ws_heartbeat_ctx=companion_hb_ctx,
                    )
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
        hb_worker_stop.set()
        hb_worker_task.cancel()
        try:
            await hb_worker_task
        except asyncio.CancelledError:
            pass
        await _shutdown_chat_ws_outbound_pump(pump_task)


@router.websocket("/ws/verify")
async def chat_completions_websocket_verify(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
    subscription_svc: SubscriptionService = Depends(deps.get_subscription_service),
):
    """
    Legacy smoke endpoint: same **outbound queue + pump** as ``/ws`` (FIFO business JSON).

    Per chat frame: **one** ``chat.completions`` call with system + user messages only (via
    ``get_chat_openai_client``). No ``Agent`` runtime, no companion pipeline, no chat_history
    persistence. Use to validate transport, queue behavior, and minimal LLM connectivity.
    """
    await websocket.accept()
    current_user = await _get_current_user_from_websocket(websocket, db)
    if current_user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    current_user = await _resolve_assumed_chat_websocket_user(
        operator=current_user,
        assume_user_id=websocket.query_params.get("assume_user_id"),
        db=db,
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
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = None
            if await _try_handle_ws_user_signed_on_frame(
                websocket,
                data,
                db=db,
                current_user=current_user,
                companion_hb_ctx=None,
            ):
                continue
            if await _handle_chat_websocket_control_json(websocket, data, tc_box):
                continue
            websocket_request = ChatWebSocketRequest.model_validate_json(raw)
            agent_id = websocket_request.agent_id
            request = _chat_request_with_merged_ws_time_context(
                websocket_request.request,
                tc_box[0],
            )

            user_messages = [msg for msg in request.messages if msg.role == "user"]
            if not user_messages:
                await outbound_queue.put(
                    {
                        "code": 400,
                        "message": "No user message found",
                        "data": None,
                        "agent_id": agent_id,
                    }
                )
                continue

            last_user_text = user_messages[-1].extract_text_content()

            agent_row = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
            if not agent_row:
                await outbound_queue.put(
                    {
                        "code": 404,
                        "message": "Agent not found",
                        "data": None,
                        "agent_id": agent_id,
                    }
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
                    model_name=model_override,
                )
            except Exception as e:
                logger.exception("ws/verify simple chat.completions failed")
                await outbound_queue.put(
                    {
                        "code": 500,
                        "message": str(e),
                        "data": None,
                        "agent_id": agent_id,
                    }
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
            response = schemas.APIResponse.success(data=data)
            response_data = response.model_dump(exclude_none=True)
            response_data["agent_id"] = agent_id
            response_data["status_line"] = await _agent_status_line_for_chat_header(
                db, agent_id
            )
            await outbound_queue.put(response_data)
    except WebSocketDisconnect:
        return
    finally:
        await _shutdown_chat_ws_outbound_pump(pump_task)


class ChatImageBizErrorData(BizError):
    description: Optional[str] = None
    suggestion: Optional[str] = None


ChatImageGenerationAPIResponse: TypeAlias = schemas.APIResponse[
    Union[
        schemas.ChatImageGenerationResponse,
        UsageLimitExceeded,
        ChatImageBizErrorData,
    ]
]


ChatMusicGenerationAPIResponse: TypeAlias = schemas.APIResponse[
    Union[
        schemas.ChatMusicGenerationResponse,
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
    request: schemas.ChatImageGenerationRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    subscription_svc: SubscriptionService = Depends(deps.get_subscription_service),
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
            return schemas.APIResponse.error(
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

        return schemas.APIResponse.success(data=result)

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"生成聊天图片失败 - Agent ID: {agent_id}, Error: {str(e)}")
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
    request: schemas.ChatMusicGenerationRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    subscription_svc: SubscriptionService = Depends(deps.get_subscription_service),
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
            return schemas.APIResponse.error(
                message=result.message, code=result.code, data=result
            )

        return schemas.APIResponse.success(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成聊天音乐失败 - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate music: {str(e)}"
        )
