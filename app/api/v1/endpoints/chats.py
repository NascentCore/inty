import json
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps
from app.api.tags import (
    ANDROID_APP_TAG,
    INTERNAL_API_TAG,
    INTY_EVAL_TAG,
    NOT_USED_TAG,
    WEB_APP_TAG,
)
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.core.chat import generate_chat_stream
from app.core.config import global_config_loaded_from_config_yaml
from app.core.user_privilege.premium_check import is_eligible_for_premium
from app.schemas.chat import ChatCompletionRequest, MessageVoteRequest
from app.schemas.response import (
    APIResponse,
    BizError,
    BusinessErrorCode,
    UsageLimitExceeded,
    create_business_error_response,
)
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.memory_service import deliver_festival_memories_for_user_agent
from app.services.global_services import subscription_service
from app.services.voice_service import voice_service

# TODO: Prefix should be /chat instead of /chats.
router = APIRouter(prefix="/chats", route_class=LoggerRoute)


@router.get(
    "/",
    response_model=List[schemas.Chat],
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
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user's chat list
    """
    chats = await chat_service.get_chats(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return chats


@router.post(
    "/",
    response_model=schemas.Chat,
    summary="Create new chat",
    description="Create new chat",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
async def create_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_in: schemas.ChatCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new chat
    """
    chat = await chat_service.create_chat(db, chat_in=chat_in, user_id=current_user.id)
    return chat


@router.delete(
    "/{chat_id}",
    response_model=schemas.Chat,
    summary="Delete chat",
    description="Delete chat",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG, NOT_USED_TAG],
)
async def delete_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete chat
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
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="Number of messages per page"),
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
        logger.debug(f"Getting Agent chat messages - Agent ID: {agent_id}")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}",
            )

        # Use unified session_id generation rule
        session_id = generate_session_id(chat.id)

        # 按需投递节日记忆提示，再拉取消息列表（新投递的提示会出现在列表中）
        try:
            await deliver_festival_memories_for_user_agent(
                db, current_user.id, agent_id
            )
        except Exception as e:
            logger.warning(f"投递节日记忆提示失败: {e}")

        # 获取分页消息
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id, limit=limit, offset=offset, user_id=current_user.id
        )

        min_ver = (
            global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
        )
        if app_version_code is not None and app_version_code < min_ver:
            messages_data["messages"] = [
                m
                for m in messages_data["messages"]
                if m.get("type") != "festival_memory_prompt"
            ]

        # 如果要求升序（旧消息在前），则不反转
        # 如果要求降序（新消息在前），则反转消息列表
        if order == "desc":
            messages_data["messages"].reverse()

        return messages_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get message records: {str(e)}"
        )


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
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> APIResponse[Dict[str, Any]]:
    """
    Update message vote (like/dislike)
    Only AI messages (role="assistant") can be voted.
    """
    try:
        # 验证 vote 值
        if request.vote is not None and request.vote not in ["like", "dislike"]:
            return APIResponse.error(
                message="Invalid vote value. Must be 'like', 'dislike', or null",
                code=400,
            )

        # Get or create chat session
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=request.agent_id
        )

        # Verify chat belongs to current user
        if chat.user_id != current_user.id:
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
            role = "user" if message_type in ["human", "HumanMessage"] else "assistant"

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
            user_id=current_user.id,
            vote=request.vote,
        )

        if not success:
            return APIResponse.error(message="Failed to update message vote", code=500)

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
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    为指定消息生成语音
    用于用户点击播放按钮时的按需语音生成
    """
    try:
        # 使用高性能的聊天专用Agent获取方法
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
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

        # 使用Agent的voice_id生成语音
        agent_voice_id = agent_data.get("voice_id")
        voice_result = await voice_service.generate_voice(
            text=message_content,
            voice_id=agent_voice_id,
            language=language,
            db=db,
            agent_gender=agent_data.get("gender"),
            user=current_user,
        )

        if not voice_result:
            # 检查是否是因为达到限制
            from app.services.global_services import subscription_service

            (
                is_allowed,
                used_count,
                limit,
            ) = await subscription_service.check_voice_generation_limit(
                db, current_user
            )
            if not is_allowed:
                from app.models.user import AuthType

                if current_user.auth_type == AuthType.GUEST:
                    # 游客用户：提示登录
                    return create_business_error_response(
                        error_info=BusinessErrorCode.GUEST_LOGIN_REQUIRED,
                        extra_data={"used_count": used_count, "limit": limit},
                    )
                else:
                    # 已登录用户：提示达到限制
                    return create_business_error_response(
                        error_info=BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED,
                        extra_data={"used_count": used_count, "limit": limit},
                    )
            raise HTTPException(status_code=500, detail="Voice generation failed")

        audio_url, audio_duration = voice_result
        logger.debug(f"按需语音生成成功: {audio_url}, 时长: {audio_duration:.2f}秒")

        # 更新chat_history中对应消息的audio_url
        # 使用try-except确保更新失败不影响API响应
        try:
            update_success = await chat_history_service.update_message_audio_url(
                db=db,
                session_id=session_id,
                message_id=message_id,
                audio_url=audio_url,
                audio_duration=audio_duration,
            )
            if update_success:
                logger.debug(f"成功更新消息{message_id}的audio_url到chat_history")
            else:
                logger.warning(f"更新消息{message_id}的audio_url到chat_history失败")
        except Exception as e:
            logger.error(f"更新chat_history的audio_url时发生异常: {str(e)}")
            # 继续执行，不影响API响应

        return APIResponse.success(
            data={
                "audio_url": audio_url,
                "message_id": message_id,
                "voice_id": agent_voice_id
                or global_config_loaded_from_config_yaml.elevenlabs.voice_id,
                "language": language,
                "audio_duration": audio_duration,  # 音频时长（秒）
                "cached": False,  # 这里可以后续实现缓存检测
                "generation_time": None,  # 可以记录生成时间
            }
        )

    except Exception as e:
        logger.error(f"按需语音生成失败: {str(e)}")
        return APIResponse.error(message=f"Voice generation failed: {str(e)}", code=500)


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
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取特定语音的信息
    """
    try:
        voice_info = await voice_service.get_voice_info(voice_id)
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
        schemas.APIResponse[schemas.ChatSettings],
        schemas.APIResponse[dict],
    ],
)
async def update_agent_chat_settings(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    settings_update: schemas.ChatSettingsUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update chat settings by Agent ID
    Input agent_id, find user's unique chat session with that Agent, update chat settings
    If chat session doesn't exist, automatically create one
    """
    try:
        logger.info(
            f"Updating Agent chat settings - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # First verify if Agent exists
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"Agent ID mismatch")

        # Get or create chat settings, then update
        # First ensure settings exist
        settings = await chat_service.get_or_create_chat_settings(
            db=db, chat_id=chat.id, user_id=current_user.id, agent_id=agent_id
        )

        subscription_status = await subscription_service.get_user_subscription_status(
            db, current_user.id
        )

        # Check if trying to update style_prompt and if user has subscription
        # style_prompt is only available for subscribed users or superusers
        if settings_update.style_prompt and not is_eligible_for_premium(
            current_user, subscription_status
        ):
            return create_business_error_response(
                error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED
            )

        # Check if trying to update premium_mode and if user has subscription
        if settings_update.premium_mode and not is_eligible_for_premium(
            current_user, subscription_status
        ):
            return create_business_error_response(
                error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED
            )

        # Then update settings
        settings = await chat_service.update_chat_settings(
            db=db, chat_id=chat.id, settings_update=settings_update
        )

        logger.info(
            f"Successfully updated Agent chat settings - Agent ID: {agent_id}, Settings ID: {settings.id}"
        )

        return schemas.APIResponse.success(data=settings)

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
    response_model=schemas.ChatSettings,
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
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get chat settings by Agent ID
    If chat session or settings don't exist, automatically create them
    """
    try:
        logger.info(
            f"Getting Agent chat settings - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # First verify if Agent exists
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        # Get or create chat settings
        settings = await chat_service.get_or_create_chat_settings(
            db=db, chat_id=chat.id, user_id=current_user.id, agent_id=agent_id
        )

        logger.info(
            f"Successfully got Agent chat settings - Agent ID: {agent_id}, Settings ID: {settings.id}"
        )

        return settings

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
    response_model=schemas.ChatDeletionResponse,
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
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除用户与指定Agent的所有聊天记录
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
    "/agents/{agent_id}/generate-image",
    deprecated=True,
    include_in_schema=False,
    response_model=schemas.APIResponse,
    summary="[Deprecated, use /api/v1/chat/images/{agent_id} instead] 基于聊天上下文生成图片",
    description="[Deprecated, use /api/v1/chat/images/{agent_id} instead] 根据Agent角色、聊天历史和用户消息生成图片，并保存到聊天历史中",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def generate_chat_image(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: schemas.ChatImageGenerationRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
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
    - 核心逻辑已提取到 `chat_service.generate_chat_image`
    """
    try:
        result = await chat_service.generate_chat_image(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            message_id=request.message_id,
            subscription_service=subscription_service,
            history_count=request.history_count,
            model=request.model,
        )

        # 检查是否返回了业务限制错误
        if isinstance(result, UsageLimitExceeded):
            # 转换为兼容现有客户端的业务错误响应格式
            return create_business_error_response(
                error_info={
                    "code": result.code,
                    "error_code": result.error_code,
                    "message": result.message,
                },
                extra_data={
                    "used_count": result.used_count,
                    "daily_limit": result.daily_limit,
                },
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
