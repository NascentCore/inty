import asyncio
import json
import logging
import time
import uuid
from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.core.chat import generate_chat_stream
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.chat import ChatCompletionRequest
from app.schemas.response import BusinessErrorCode, create_business_error_response
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.global_services import subscription_service
from app.services.voice_service import voice_service
from app.utils.timing import Timer, log_time

router = APIRouter(prefix="/chat", route_class=LoggerRoute)


class ChatMessage(BaseModel):
    """Chat message model for OpenAI-style responses"""

    role: str
    content: str
    id: Optional[str] = None
    meta_data: Optional[dict] = None
    timestamp: Optional[str] = None
    audio_url: Optional[str] = None


class ChatChoice(BaseModel):
    """Chat choice model for OpenAI-style responses"""

    index: int
    message: ChatMessage
    finish_reason: str


class ChatUsage(BaseModel):
    """Token usage model for OpenAI-style responses"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI-style chat completion response model"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    # 当前只会返回 1 个 choice，但是保留列表，以便未来实现其他功能，比如 ai 帮答。
    choices: List[ChatChoice]
    usage: ChatUsage


@router.post(
    "/completions/{agent_id}",
    response_model=schemas.APIResponse[ChatCompletionResponse],
    summary="返回与指定 Agent 聊天的下一条消息",
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
    if request.stream:
        raise HTTPException(status_code=400, detail="Stream is not supported")

    try:
        import time

        request_handling_timer = Timer("请求处理")
        logger.debug(
            f"开始处理聊天请求 - Agent ID: {agent_id}, User ID: {current_user.id}"
        )
        logger.debug(f"请求参数: {request.dict()}")
        logger.debug(f"request.messages详情: {request.messages}")
        logger.debug(
            f"request.messages数量: {len(request.messages) if request.messages else 0}"
        )

        # 优化：简化Agent验证，在创建Agent实例时验证
        # 简化查询，只获取基本字段
        with log_time(f"简化Agent验证: {agent_id}"):
            result = await db.execute(
                select(models.Agent.id, models.Agent.name).where(
                    models.Agent.id == agent_id
                )
            )
        agent_basic = result.first()
        if not agent_basic:
            logger.error(f"Agent未找到: {agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")

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
            logger.error("请求中没有用户消息")
            logger.error(f"所有消息的role: {[msg.role for msg in request.messages]}")
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

        is_allowed, used_count, daily_limit = (
            await subscription_service.check_chat_limit(db, current_user)
        )

        if not is_allowed:
            # 在返回错误前，先保存用户消息到聊天历史
            # TODO: 考虑直接丢弃比较合适？但是会影响前后端一致性，需要跟 @zhiwei 讨论。
            try:
                chat_history_service.add_user_message(session_id, last_user_message)
                logger.debug(f"用户消息已保存到历史记录: {session_id}")
            except Exception as e:
                logger.warning(f"保存用户消息失败: {str(e)}")

            return create_business_error_response(
                error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED,
                extra_data={"used_count": used_count, "daily_limit": daily_limit},
            )

        logger.debug(f"开始非流式聊天处理: session_id={session_id}")
        chat_processing_start = time.time()

        # 并行获取聊天设置和AI回复
        try:
            settings_task = asyncio.create_task(
                chat_service.get_or_create_chat_settings(
                    db, chat.id, current_user.id, agent_id
                )
            )

            # 先获取设置，然后传递给AI任务
            chat_settings = await settings_task
            logger.debug(f"chat_settings: {chat_settings.__dict__}")

            ai_task = asyncio.create_task(
                agent.chat(
                    user_id=current_user.id,
                    session_id=session_id,
                    messages=messages,
                    chat_settings=chat_settings,
                )
            )

            # 等待任务完成
            response_content = await ai_task
            chat_processing_time = time.time() - chat_processing_start
            logger.debug(
                f"Agent聊天响应成功: {response_content[:100]}..., 耗时: {chat_processing_time:.3f}秒"
            )
            logger.debug(
                f"聊天设置获取成功: voice_enabled={chat_settings.voice_enabled}"
            )

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
                    )
                if voice_result:
                    audio_url, audio_duration = voice_result
            else:
                logger.debug("语音未启用，跳过语音生成")

        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")
            # 语音生成失败不影响聊天功能

        # 记录聊天使用情况
        try:
            logger.debug(f"记录聊天使用情况: user_id={current_user.id}")
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
            latest_message_info = await chat_history_service.get_latest_ai_message_info(
                db, session_id
            )
        except Exception as e:
            logger.warning(f"获取最新消息信息失败: {str(e)}")
            latest_message_info = None

        # 构建响应消息
        logger.debug("构建聊天响应消息")
        message = {"role": "assistant", "content": response_content}

        # 添加消息的完整信息（id, meta_data, timestamp等）
        if latest_message_info:
            message["id"] = latest_message_info["id"]
            message["meta_data"] = latest_message_info["meta_data"]
            message["timestamp"] = latest_message_info["timestamp"]
            # 如果数据库中有audio_url，使用数据库的，否则使用新生成的
            if latest_message_info["audio_url"]:
                message["audio_url"] = latest_message_info["audio_url"]
            elif audio_url:
                message["audio_url"] = audio_url
        else:
            # 如果获取失败，至少添加生成的语音URL
            if audio_url:
                message["audio_url"] = audio_url

        if audio_url or (latest_message_info and latest_message_info.get("audio_url")):
            logger.debug(f"响应包含语音URL: {message.get('audio_url')}")

        timing_message = request_handling_timer.stop()
        logger.debug(
            f"聊天请求处理成功: agent_id={agent_id}, response_length={len(response_content)}, {timing_message}"
        )
        # Create ChatMessage object
        chat_message = ChatMessage(
            role=message["role"],
            content=message["content"],
            id=message.get("id"),
            meta_data=message.get("meta_data"),
            timestamp=message.get("timestamp"),
            audio_url=message.get("audio_url"),
        )

        # Create ChatChoice object
        chat_choice = ChatChoice(index=0, message=chat_message, finish_reason="stop")

        # Create ChatUsage object
        chat_usage = ChatUsage(
            prompt_tokens=len(last_user_message.split()),
            completion_tokens=len(response_content.split()),
            total_tokens=len(last_user_message.split()) + len(response_content.split()),
        )

        # Create ChatCompletionResponse object
        response_data = ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",  # 保持随机生成的外层ID
            object="chat.completion",
            created=int(time.time()),
            model=request.model,
            choices=[chat_choice],
            usage=chat_usage,
        )

        return schemas.APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"聊天请求处理失败: {str(e)}")
        logger.exception("聊天请求异常详细信息:")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
