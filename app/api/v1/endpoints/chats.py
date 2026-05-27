import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_settings import ChatSettings
from app.api import deps
from app.api.tags import (
    ANDROID_APP_TAG,
    INTERNAL_API_TAG,
    INTY_EVAL_TAG,
    NOT_USED_TAG,
    WEB_APP_TAG,
)
from app.api.utils.feature_gating import (
    is_daily_memory_enabled,
    is_festival_memory_enabled,
)
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.core.agent.prompts import (
    USER_FACING_CHAT_MODE_IDS,
    get_user_facing_chat_mode_options,
)
from app.core.chat import generate_chat_stream
from app.core.config import global_config_loaded_from_config_yaml
from app.core.voice.tts_api import is_gemini_voice
from app.schemas.chat import (
    ChatCompletionRequest,
    MessageVoteRequest,
    SurpriseSnapUnlockRequest,
)
from app.schemas.response import (
    APIResponse,
    BizError,
    BusinessErrorCode,
    UsageLimitExceeded,
    create_business_error_response,
)
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.memory_service import (
    deliver_daily_memories_for_user_agent,
    deliver_festival_memories_for_user_agent,
)
from app.services.subscription_service import SubscriptionService
from app.services.surprise_snap_service import (
    get_unlocked_surprise_snap_message_ids,
    record_surprise_snap_unlock,
)
from app.schemas import chat as chat_schemas
from app.schemas.chat import Chat as ChatSchema
from app.schemas.chat import ChatCreate
from app.schemas.chat import ChatDeletionResponse
from app.schemas.chat import ChatSettings
from app.schemas.chat import ChatSettingsUpdate
from app.schemas.chat import ClearMessagesRequest
from app.schemas.chat import ClearMessagesResponse
from app.schemas.user import User as UserSchema
from app.services.voice_service import (
    VoiceService,
    get_voice_message_narration_mode_from_agent_settings,
)

# TODO: Prefix should be /chat instead of /chats.
router = APIRouter(prefix="/chats", route_class=LoggerRoute)
CHAT_SETTINGS_DEFAULT_VOICE_SENTINEL = "default"


def _normalize_chat_settings_voice_id(
    settings_update: ChatSettingsUpdate,
) -> ChatSettingsUpdate:
    """
    Normalize default voice sentinel into explicit null.
    """
    raw_voice_id = settings_update.voice_id
    if raw_voice_id is None:
        return settings_update

    normalized_voice_id = raw_voice_id.strip()
    if (
        normalized_voice_id == ""
        or normalized_voice_id.lower() == CHAT_SETTINGS_DEFAULT_VOICE_SENTINEL
    ):
        return settings_update.model_copy(update={"voice_id": None})

    if normalized_voice_id == raw_voice_id:
        return settings_update

    return settings_update.model_copy(update={"voice_id": normalized_voice_id})


@router.get(
    "/modes",
    response_model=List[chat_schemas.ChatModeOption],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
    summary="List conversation modes",
    description="Return the three user-facing chat modes (id, short_name, name, description). If agent_id is provided and the agent default mode is not in the three, returns empty list.",
)
async def list_chat_modes(
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: Optional[str] = Query(
        None,
        description="When set, return empty list if agent default mode is not in the three user-facing modes",
    ),
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> Any:
    if agent_id:
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if (
            not agent_db
            or getattr(agent_db, "mode_prompt", None)
            not in USER_FACING_CHAT_MODE_IDS
        ):
            return []
    opts = get_user_facing_chat_mode_options()
    return [
        chat_schemas.ChatModeOption(
            id=p.id,
            short_name=p.short_name,
            name=p.name,
            description=p.description,
        )
        for p in opts
    ]


@router.get(
    "/",
    response_model=List[ChatSchema],
    summary="Get current user's chat list",
    description="Get current user's chat list",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
async def list_chats(
    db: AsyncSession = Depends(deps.get_async_db),
    # Start index of the query, 0-based
    skip: int = 0,
    # Upper limit of the number of chats to return
    limit: int = 100,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> Any:
    """
    Get current user's chat list (evaluation can pass X-Assume-User-Id to list another user's chats).
    """
    chats = await chat_service.get_chats(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return chats


@router.post(
    "/",
    response_model=ChatSchema,
    summary="Create new chat",
    description="Create new chat",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
async def create_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_in: ChatCreate,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> Any:
    """
    Create new chat (evaluation can pass X-Assume-User-Id to create as another user).
    """
    chat = await chat_service.create_chat(
        db, chat_in=chat_in, user_id=current_user.id
    )
    return chat


@router.delete(
    "/{chat_id}",
    response_model=ChatSchema,
    summary="Delete chat",
    description="Delete chat",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG, NOT_USED_TAG],
)
async def delete_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> Any:
    """
    Delete chat (evaluation can pass X-Assume-User-Id).
    """
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat = await chat_service.delete_chat(db, db_chat=chat)
    return chat


@router.get(
    "/agents/status",
    deprecated=True,
    include_in_schema=False,
    description="No record of who is using this",
    tags=[INTERNAL_API_TAG, NOT_USED_TAG],
)
async def get_agent_status(
    current_user: UserSchema = Depends(deps.get_current_active_user),
):
    """
    Get Agent manager status
    """
    return {
        "active_agents": agent_manager.get_agent_count(),
        "max_agents": agent_manager.max_agents,
        "cleanup_interval": agent_manager.cleanup_interval,
        "max_idle_time": agent_manager.max_idle_time,
    }


@router.get(
    "/agents/{agent_id}/messages",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
    summary="Get Agent Chat Messages",
    description="Get only chat message records by Agent ID (lighter interface)",
)
async def get_agent_chat_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
    limit: int = Query(
        20, ge=1, le=100, description="Number of messages per page"
    ),
    offset: int = Query(0, ge=0, description="Offset"),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort order: asc=old messages first, desc=new messages first",
    ),
    app_version_code: Optional[int] = Header(None, alias="appVersionCode"),
) -> Any:
    """
    Get only chat message records by Agent ID (lighter interface)
    If user hasn't created a session with this Agent, automatically create one
    Specifically for scrolling load
    """
    try:
        # 先缓存 user_id，避免后续数据库 rollback 使 ORM 实例过期后再读属性触发 MissingGreenlet
        current_user_id = current_user.id
        logger.debug(f"Getting Agent chat messages - Agent ID: {agent_id}")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user_id, agent_id=agent_id
        )

        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(
                f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}",
            )

        # Use unified session_id generation rule
        session_id = generate_session_id(chat.id)

        # 仅当客户端提供版本且满足最低要求时按需投递；未传版本或旧版不投递，delivery_at 保持 null
        if is_festival_memory_enabled(app_version_code):
            try:
                await deliver_festival_memories_for_user_agent(
                    db, current_user_id, agent_id
                )
            except Exception as e:
                await db.rollback()
                logger.warning(f"投递节日记忆提示失败: {e}")

        if is_daily_memory_enabled(app_version_code):
            try:
                await deliver_daily_memories_for_user_agent(
                    db, current_user_id, agent_id
                )
            except Exception as e:
                await db.rollback()
                logger.warning(f"投递日常记忆提示失败: {e}")

        unlocked_ids = await get_unlocked_surprise_snap_message_ids(
            db, current_user_id
        )
        messages_data = await asyncio.to_thread(
            chat_history_service.get_messages_paginated,
            session_id=session_id,
            limit=limit,
            offset=offset,
            user_id=current_user_id,
            unlocked_surprise_snap_message_ids=unlocked_ids,
        )

        # 如果客户端版本不支持节日记忆，则不返回节日记忆消息，即便数据库中有节日记忆消息。
        # 这种情况不会发生，因为客户端会自动升级到支持节日记忆的版本。

        # 如果要求升序（旧消息在前），则不反转
        # 如果要求降序（新消息在前），则反转消息列表
        if order == "desc":
            messages_data["messages"].reverse()

        return messages_data

    except Exception as e:
        logger.exception(f"Failed to get message records: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get message records: {str(e)}"
        )


@router.post(
    "/surprise-snap/unlock",
    response_model=APIResponse[dict],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
    summary="Record Surprise Snap unlock",
    description="Free user uses credit to unlock a surprise_snap message (credit deduction on app). Backend only records unlock state.",
)
async def surprise_snap_unlock(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    body: SurpriseSnapUnlockRequest,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> Any:
    ok = await record_surprise_snap_unlock(db, current_user.id, body.message_id)
    if not ok:
        raise HTTPException(
            status_code=403,
            detail="Message not found or not a surprise_snap or not your chat",
        )
    return APIResponse.success(data={"unlocked": True})


@router.post(
    "/messages/vote",
    response_model=APIResponse[Dict[str, Any]],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
    summary="Update Message Vote",
    description="Set, toggle, or remove vote (like/dislike) for a message. Only AI messages can be voted.",
)
async def update_message_vote(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    request: MessageVoteRequest,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> APIResponse[Dict[str, Any]]:
    """
    Update message vote (like/dislike)
    Only AI messages (role="assistant") can be voted.
    """
    try:
        current_user_id = current_user.id

        # 验证 vote 值
        if request.vote is not None and request.vote not in ["like", "dislike"]:
            return APIResponse.error(
                message="Invalid vote value. Must be 'like', 'dislike', or null",
                code=400,
            )

        # Get or create chat session
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user_id, agent_id=request.agent_id
        )

        # Verify chat belongs to current user
        if chat.user_id != current_user_id:
            return APIResponse.error(message="Forbidden", code=403)

        # Generate session_id
        session_id = generate_session_id(chat.id)

        # 验证消息是否存在且为 AI 消息
        conn = chat_history_service.get_chat_history_connection()
        with conn.cursor() as cur:
            check_query = """
                SELECT id, message, meta_data
                FROM chat_history 
                WHERE session_id = %s AND id = %s
            """
            cur.execute(check_query, (session_id, request.message_id))
            row = cur.fetchone()

            if not row:
                return APIResponse.error(message="Message not found", code=404)

            # 解析消息类型
            message_raw = row[1]
            if isinstance(message_raw, str):
                message_data = json.loads(message_raw)
            elif isinstance(message_raw, dict):
                message_data = message_raw
            else:
                message_data = json.loads(str(message_raw))

            message_type = message_data.get("type", "human")
            role = (
                "user"
                if message_type in ["human", "HumanMessage"]
                else "assistant"
            )

            # 仅允许对 AI 消息进行投票
            if role != "assistant":
                return APIResponse.error(
                    message="Only AI messages can be voted", code=400
                )

        # 更新投票
        success = await chat_history_service.update_message_vote(
            db=db,
            session_id=session_id,
            message_id=request.message_id,
            user_id=current_user_id,
            vote=request.vote,
        )

        if not success:
            return APIResponse.error(
                message="Failed to update message vote", code=500
            )

        return APIResponse.success(
            data={"vote": request.vote}, message="Vote updated successfully"
        )

    except Exception as e:
        logger.error(f"更新消息投票失败: {str(e)}")
        return APIResponse.error(
            message=f"Failed to update message vote: {str(e)}", code=500
        )


@router.post(
    "/agents/{agent_id}/messages/{message_id}/voice",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
    summary="Generate Message Voice",
    description="Generate voice for a message",
)
async def generate_message_voice(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    message_id: str,
    language: str = Query("zh", description="语言代码"),
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
    voice_svc: VoiceService = Depends(deps.get_voice_service),
):
    """
    为指定消息生成语音（evaluation 可传 X-Assume-User-Id）
    用于用户点击播放按钮时的按需语音生成
    """
    try:
        # 使用高性能的聊天专用Agent获取方法
        agent_data = await agent_service.get_agent_for_chat(
            db, agent_id=agent_id
        )
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 获取用户与该Agent的会话
        chat = await chat_service.get_chat_by_user_and_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # 从聊天历史中获取消息内容
        session_id = generate_session_id(chat.id)
        message_content = await chat_history_service.get_message_content(
            db=db, session_id=session_id, message_id=message_id
        )

        if not message_content:
            raise HTTPException(status_code=404, detail="Message not found")

        selected_chat_voice_id = (
            chat.settings.voice_id if getattr(chat, "settings", None) else None
        )
        agent_voice_id = agent_data.get("voice_id")
        resolved_voice_id = selected_chat_voice_id or agent_voice_id
        voice_message_narration_mode = (
            get_voice_message_narration_mode_from_agent_settings(
                agent_data.get("settings")
            )
        )
        from app.models.user import AuthType
        from app.services.chat_assistant_voice import produce_voice_for_user

        voice_result, is_allowed, used_count, limit = (
            await produce_voice_for_user(
                voice_svc=voice_svc,
                db=db,
                user=current_user,
                text=message_content,
                voice_id=resolved_voice_id,
                language=language,
                agent_gender=agent_data.get("gender"),
                voice_message_narration_mode=voice_message_narration_mode,
            )
        )

        if not is_allowed:
            if current_user.auth_type == AuthType.GUEST:
                return create_business_error_response(
                    error_info=BusinessErrorCode.GUEST_LOGIN_REQUIRED,
                    extra_data={"used_count": used_count, "limit": limit},
                )
            return create_business_error_response(
                error_info=BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED,
                extra_data={"used_count": used_count, "limit": limit},
            )

        if not voice_result:
            raise HTTPException(
                status_code=500, detail="Voice generation failed"
            )

        audio_url = voice_result.gcs_http_url
        audio_duration = voice_result.duration_seconds
        logger.debug(
            f"按需语音生成成功: {audio_url}, gcs_url={voice_result.gcs_url}, 时长: {audio_duration:.2f}秒"
        )

        # 更新chat_history中对应消息的audio_url
        # 使用try-except确保更新失败不影响API响应
        try:
            update_success = (
                await chat_history_service.update_message_audio_url(
                    db=db,
                    session_id=session_id,
                    message_id=message_id,
                    audio_url=audio_url,
                    audio_duration=audio_duration,
                )
            )
            if update_success:
                logger.debug(
                    f"成功更新消息{message_id}的audio_url到chat_history"
                )
            else:
                logger.warning(
                    f"更新消息{message_id}的audio_url到chat_history失败"
                )
        except Exception as e:
            logger.error(f"更新chat_history的audio_url时发生异常: {str(e)}")
            # 继续执行，不影响API响应

        return APIResponse.success(
            data={
                "audio_url": audio_url,
                "gcs_url": voice_result.gcs_url,
                "gcs_http_url": voice_result.gcs_http_url,
                "message_id": message_id,
                "voice_id": resolved_voice_id
                or global_config_loaded_from_config_yaml.elevenlabs.voice_id,
                "language": language,
                "audio_duration": audio_duration,  # 音频时长（秒）
                "cached": False,  # 这里可以后续实现缓存检测
                "generation_time": None,  # 可以记录生成时间
            }
        )

    except Exception as e:
        logger.error(f"按需语音生成失败: {str(e)}")
        return APIResponse.error(
            message=f"Voice generation failed: {str(e)}", code=500
        )


@router.get(
    "/voices/{voice_id}",
    deprecated=True,
    include_in_schema=True,
    tags=[INTERNAL_API_TAG, NOT_USED_TAG],
    summary="Get Voice Info",
    description="Get voice info by voice_id",
)
async def get_voice_info(
    voice_id: str,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
    voice_svc: VoiceService = Depends(deps.get_voice_service),
):
    """
    获取特定语音的信息
    """
    try:
        voice_info = await voice_svc.get_voice_info(voice_id)
        if not voice_info:
            raise HTTPException(status_code=404, detail="Voice not found")

        return voice_info
    except Exception as e:
        logger.error(f"获取语音信息失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get voice info: {str(e)}"
        )


@router.put(
    "/agents/{agent_id}/settings",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
    summary="Update Chat Settings by Agent ID",
    description=(
        "We do not use chat_id to get settings, because we only support 1 chat per agent."
        "TODO: We should switch to /chats/{chat_id}/settings"
    ),
    response_model=Union[
        # TODO: Why do we use union here?
        APIResponse[ChatSettings],
        APIResponse[dict],
    ],
)
async def update_agent_chat_settings(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    settings_update: ChatSettingsUpdate,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
) -> Any:
    """
    Update chat settings by Agent ID
    Input agent_id, find user's unique chat session with that Agent, update chat settings
    If chat session doesn't exist, automatically create one
    """
    try:
        current_user_id = current_user.id
        current_user_is_superuser = bool(current_user.is_superuser)

        logger.info(
            f"Updating Agent chat settings - Agent ID: {agent_id}, User ID: {current_user_id}"
        )

        # First verify if Agent exists
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user_id, agent_id=agent_id
        )

        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(
                f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}"
            )
            raise HTTPException(status_code=500, detail=f"Agent ID mismatch")

        # Get or create chat settings, then update
        # First ensure settings exist
        settings = await chat_service.get_or_create_chat_settings(
            db=db, chat_id=chat.id, user_id=current_user_id, agent_id=agent_id
        )

        subscription_status = (
            await subscription_svc.get_user_subscription_status(
                db, current_user_id
            )
        )

        # Check if trying to update style_prompt and if user has subscription
        # style_prompt is only available for subscribed users or superusers
        if settings_update.style_prompt and not (
            current_user_is_superuser or subscription_status.is_subscribed
        ):
            return create_business_error_response(
                error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED
            )

        # Check if trying to update premium_mode and if user has subscription
        if settings_update.premium_mode and not (
            current_user_is_superuser or subscription_status.is_subscribed
        ):
            return create_business_error_response(
                error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED
            )

        settings_update = _normalize_chat_settings_voice_id(settings_update)

        if settings_update.voice_id is not None and not is_gemini_voice(
            settings_update.voice_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Only Gemini voices are supported in chat settings for now.",
            )

        if (
            settings_update.chat_mode is not None
            and settings_update.chat_mode not in USER_FACING_CHAT_MODE_IDS
        ):
            raise HTTPException(
                status_code=400,
                detail="chat_mode must be one of: "
                + ", ".join(USER_FACING_CHAT_MODE_IDS),
            )

        # Then update settings
        settings = await chat_service.update_chat_settings(
            db=db, chat_id=chat.id, settings_update=settings_update
        )

        logger.info(
            f"Successfully updated Agent chat settings - Agent ID: {agent_id}, Settings ID: {settings.id}"
        )

        return APIResponse.success(data=settings)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update Agent chat settings - Agent ID: {agent_id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to update chat settings: {str(e)}"
        )


# TODO: Should we switch to /chats/{chat_id}/settings?
@router.get(
    "/agents/{agent_id}/settings",
    response_model=chat_schemas.ChatSettingsInDB,
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
    summary="Get Agent Chat Settings",
    description=(
        "[Deprecated, use /chats/{chat_id}/settings instead] Get chat settings by Agent ID, bause we only support 1 chat per agent, "
        "so we do not use chat_id to get settings"
    ),
)
async def get_agent_chat_settings(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> Any:
    """
    Get chat settings by Agent ID (evaluation can pass X-Assume-User-Id)
    If chat session or settings don't exist, automatically create them
    """
    try:
        current_user_id = current_user.id

        logger.info(
            f"Getting Agent chat settings - Agent ID: {agent_id}, User ID: {current_user_id}"
        )

        # First verify if Agent exists
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user_id, agent_id=agent_id
        )

        # Get or create chat settings
        settings = await chat_service.get_or_create_chat_settings(
            db=db, chat_id=chat.id, user_id=current_user_id, agent_id=agent_id
        )

        agent_default_mode = getattr(agent_db, "mode_prompt", None)
        if agent_default_mode not in USER_FACING_CHAT_MODE_IDS:
            chat_mode_value = None
        else:
            chat_mode_value = settings.chat_mode or agent_default_mode

        response = chat_schemas.ChatSettingsInDB.model_validate(
            settings
        ).model_copy(update={"chat_mode": chat_mode_value})

        logger.info(
            f"Successfully got Agent chat settings - Agent ID: {agent_id}, Settings ID: {settings.id}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get Agent chat settings - Agent ID: {agent_id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat settings: {str(e)}"
        )


# TODO: Should we switch to /chats/{chat_id}?
@router.delete(
    "/agents/{agent_id}/chats",
    response_model=ChatDeletionResponse,
    deprecated=True,
    include_in_schema=False,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
    summary="Delete Agent Chats",
    description="[Deprecated, use /chats/{chat_id} instead] Delete all chats by Agent ID",
)
async def delete_agent_chats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> Any:
    """
    删除用户与指定Agent的所有聊天记录（evaluation 可传 X-Assume-User-Id）
    包括聊天会话、聊天设置和聊天历史
    """
    try:
        logger.info(
            f"删除Agent聊天记录 - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # 首先验证Agent是否存在
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 调用service层删除聊天记录
        result = await chat_service.delete_chats_by_agent_id(
            db=db, agent_id=agent_id, user_id=current_user.id
        )

        logger.info(
            f"Agent聊天记录删除完成 - Agent ID: {agent_id}, User ID: {current_user.id}, "
            f"删除结果: {result}"
        )

        return {"success": True, "message": "聊天记录删除成功", "data": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"删除Agent聊天记录失败 - Agent ID: {agent_id}, User ID: {current_user.id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to delete chat record: {str(e)}"
        )


@router.post(
    "/agents/{agent_id}/clear-messages",
    response_model=ClearMessagesResponse,
    include_in_schema=True,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
    summary="Clear Agent Chat Messages",
    description="Clear chat messages by Agent ID, currently used by inty-eval, probably will be used by inty app as well.",
)
async def clear_agent_chat_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ClearMessagesRequest,
    current_user: UserSchema = Depends(deps.get_effective_user_for_eval),
) -> Any:
    """
    清除指定Agent聊天会话中的消息记录（软删除）
    支持三种方式：
    1. 通过消息ID清除该ID之后的所有消息
    2. 通过时间戳清除该时间之后的所有消息
    3. 不传参数时清除全部消息
    """
    try:
        logger.info(
            f"清除Agent聊天消息 - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # 验证请求参数：不能同时提供 message_id 和 timestamp
        if request.message_id and request.timestamp:
            raise HTTPException(
                status_code=400,
                detail="Provide either message_id or timestamp, not both",
            )

        # 验证Agent是否存在
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 获取用户与该Agent的聊天会话
        chat = await chat_service.get_chat_by_user_and_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        if not chat:
            raise HTTPException(
                status_code=404,
                detail="Chat session for this agent was not found",
            )

        # 生成session_id
        session_id = generate_session_id(chat.id)

        # 执行清除操作
        if request.message_id is not None:
            # 按消息ID清除
            result = chat_history_service.clear_messages_after_id(
                session_id=session_id, message_id=request.message_id
            )
        elif request.timestamp is not None:
            # 按时间戳清除
            result = chat_history_service.clear_messages_after_timestamp(
                session_id=session_id, timestamp=request.timestamp
            )
        else:
            # 清除全部消息
            result = chat_history_service.clear_all_messages(
                session_id=session_id
            )

        # 如果清除操作成功，同时清空 debug_messages 字段
        if result.get("success", False):
            chat.debug_messages = None
            await db.commit()
            logger.debug(f"已清空 debug_messages 字段 - Chat ID: {chat.id}")

        logger.info(f"消息清除操作完成 - Agent ID: {agent_id}, 结果: {result}")

        return ClearMessagesResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"清除Agent聊天消息失败 - Agent ID: {agent_id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to clear messages: {str(e)}"
        )
