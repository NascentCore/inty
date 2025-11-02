import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.core.config import global_config_loaded_from_config_yaml
from app.models.user import AuthType
from app.schemas.chat import ChatCompletionRequest
from app.schemas.response import BusinessErrorCode, create_business_error_response
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.global_services import subscription_service
from app.services.voice_service import voice_service
from app.utils.timing import Timer, log_time

router = APIRouter(prefix="/chat", route_class=LoggerRoute)


def _handle_subscription_limit_error(
    session_id: str,
    last_user_message: str,
    current_user: schemas.User,
    used_count: int,
    daily_limit: int,
) -> schemas.APIResponse:
    """处理订阅限制错误"""
    try:
        chat_history_service.add_user_message(session_id, last_user_message)
        logger.debug(f"用户消息已保存到历史记录: {session_id}")
    except Exception as e:
        logger.warning(f"保存用户消息失败: {str(e)}")

    if current_user.auth_type == AuthType.GUEST:
        return create_business_error_response(
            error_info=BusinessErrorCode.GUEST_LOGIN_REQUIRED,
            extra_data={"used_count": used_count, "daily_limit": daily_limit},
        )
    else:
        return create_business_error_response(
            error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED,
            extra_data={"used_count": used_count, "daily_limit": daily_limit},
        )


def _build_chat_response(
    response_content: str,
    last_user_message: str,
    latest_message_info: Optional[dict],
    audio_url: Optional[str],
    request: ChatCompletionRequest,
) -> dict:
    """构建聊天响应数据"""
    message = {"role": "assistant", "content": response_content}

    if latest_message_info:
        message["id"] = latest_message_info["id"]
        message["meta_data"] = latest_message_info["meta_data"]
        message["timestamp"] = latest_message_info["timestamp"]
        message["audio_url"] = latest_message_info["audio_url"] or audio_url
    elif audio_url:
        message["audio_url"] = audio_url

    if message.get("audio_url"):
        logger.debug(f"响应包含语音URL: {message['audio_url']}")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": len(last_user_message.split()),
            "completion_tokens": len(response_content.split()),
            "total_tokens": len(last_user_message.split())
            + len(response_content.split()),
        },
    }


@router.post(
    "/completions/{agent_id}",
    response_model=schemas.APIResponse[dict],
    deprecated=True,
    summary="[Deprecated use /api/v2/chat/completions/{agent_id} instead] 返回与指定 Agent 聊天的下一条消息",
    description="可以处理包括图片在内的各种消息类型，媒体类型应该先上传，然后将 URL 作为索引发送到此 API",
)
async def agent_chat_completions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ChatCompletionRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    基于Agent ID的OpenAI风格聊天接口
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

        last_user_message = user_messages[-1].content
        messages = {"messages": [HumanMessage(content=last_user_message)]}

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

        session_id = generate_session_id(chat.id)

        with log_time(f"订阅检查: user_id={current_user.id}"):
            is_allowed, used_count, daily_limit = (
                await subscription_service.check_chat_limit(db, current_user)
            )

        if not is_allowed:
            return _handle_subscription_limit_error(
                session_id, last_user_message, current_user, used_count, daily_limit
            )

        # 获取聊天设置和AI回复
        try:
            with log_time(f"获取聊天设置: chat_id={chat.id}"):
                chat_settings = await chat_service.get_or_create_chat_settings(
                    db, chat.id, current_user.id, agent_id
                )

            with log_time(f"AI聊天处理: session_id={session_id}"):
                response_content = await agent.chat(
                    user_id=current_user.id,
                    session_id=session_id,
                    messages=messages,
                    chat_settings=chat_settings,
                )

            logger.debug(f"Agent聊天响应成功: {response_content[:100]}...")

        except Exception as e:
            logger.error(f"Agent聊天处理失败: {str(e)}")
            raise

        # 语音生成逻辑 - 根据chat_settings.voice_enabled决定是否自动播放
        audio_url = None
        audio_duration = None
        try:
            # 语音自动播放逻辑：chat_settings.voice_enabled = true 时自动生成语音
            if chat_settings.voice_enabled:
                # TODO: 添加一个默认语音 ID
                agent_voice_id = agent_data.get("voice_id")

                with log_time(
                    f"语音生成: voice_id={agent_voice_id}, text_length={len(response_content)}, language={request.language}"
                ):
                    voice_result = await voice_service.generate_voice(
                        text=response_content,
                        voice_id=agent_voice_id,
                        language=request.language,
                        db=db,
                        agent_gender=agent_data.get("gender"),
                        user=current_user,
                    )
                if voice_result:
                    audio_url, audio_duration = voice_result
                else:
                    logger.warning(
                        f"用户 {current_user.id} 语音生成失败或达到限制，聊天文本正常返回"
                    )
            else:
                logger.debug("语音未启用，跳过语音生成")

        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")
            # 语音生成失败不影响聊天功能

        # 记录聊天使用情况
        try:
            with log_time(f"记录使用情况: user_id={current_user.id}"):
                await subscription_service.record_usage(
                    db,
                    current_user.id,
                    "chat",
                    1,
                    extra_data={
                        "agent_id": agent_id,
                        "message_length": len(last_user_message),
                    },
                )
            logger.debug("聊天使用情况记录成功")
        except Exception as e:
            logger.warning(f"记录聊天使用情况失败: {str(e)}")

        # 获取最新AI消息的完整信息
        try:
            with log_time(f"获取最新消息: session_id={session_id}"):
                latest_message_info = (
                    await chat_history_service.get_latest_ai_message_info(
                        db, session_id
                    )
                )
        except Exception as e:
            logger.warning(f"获取最新消息信息失败: {str(e)}")
            latest_message_info = None

        # 构建响应
        data = _build_chat_response(
            response_content, last_user_message, latest_message_info, audio_url, request
        )

        timing_message = request_handling_timer.stop()
        logger.debug(f"聊天请求完成: agent_id={agent_id}, {timing_message}")

        return schemas.APIResponse.success(data=data)

    except Exception as e:
        logger.error(f"聊天请求处理失败: {str(e)}")
        logger.exception("聊天请求异常详细信息:")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post(
    "/images/{agent_id}",
    response_model=schemas.APIResponse[schemas.ChatImageGenerationResponse],
    summary="基于聊天上下文生成图片",
    description=(
        "根据Agent角色、聊天历史和用户消息生成图片，并保存到聊天历史中。"
        "注意：路径参数 `agent_id` 仅作为目前的名称，实际应为 `chat_id`。"
        "本 API 拷贝自 `app/api/v1/endpoints/chats.py::generate_chat_image`（第1170-1325行）。"
    ),
    tags=["inty-eval"],
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
    - 路径参数 `agent_id` 仅作为目前的名称，实际应为 `chat_id`
    - 本 API 拷贝自 `app/api/v1/endpoints/chats.py::generate_chat_image`（第1170-1325行）
    - 核心逻辑已提取到 `chat_service.generate_chat_image`
    """
    try:
        result = await chat_service.generate_chat_image(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            message_id=request.message_id,
            history_count=request.history_count,
        )

        # 检查是否是业务错误响应
        if isinstance(result, dict) and result.get("_is_business_error"):
            return result["response"]

        return schemas.APIResponse.success(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成聊天图片失败 - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate image: {str(e)}"
        )
