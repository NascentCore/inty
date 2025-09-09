import asyncio
import json
import logging
import time
import uuid
from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
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
from app.services.voice_cache_service import voice_cache_service
from app.services.voice_cleanup_service import voice_cleanup_service
from app.services.voice_service import voice_service

from loguru import logger

router = APIRouter(prefix="/chat", route_class=LoggerRoute)
@router.post(
    "/completions/{agent_id}",
    response_model=schemas.APIResponse[dict],
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

        request_start_time = time.time()
        logger.debug(
            f"开始处理聊天请求 - Agent ID: {agent_id}, User ID: {current_user.id}"
        )
        logger.debug(f"请求参数: {request.dict()}")
        logger.debug(f"request.messages详情: {request.messages}")
        logger.debug(
            f"request.messages数量: {len(request.messages) if request.messages else 0}"
        )

        # 优化：简化Agent验证，在创建Agent实例时验证
        agent_query_start = time.time()
        logger.debug(f"简化Agent验证: {agent_id}")

        # 简化查询，只获取基本字段
        result = await db.execute(
            select(models.Agent.id, models.Agent.name).where(
                models.Agent.id == agent_id
            )
        )
        agent_basic = result.first()
        if not agent_basic:
            logger.error(f"Agent未找到: {agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")

        agent_query_time = time.time() - agent_query_start
        logger.debug(f"Agent验证成功: {agent_basic[1]}, 耗时: {agent_query_time:.3f}秒")
        # 添加日志记录传入的agent_id
        logger.debug(f"请求的Agent ID: {agent_id}")

        # 获取或创建与该Agent的唯一会话
        chat_session_start = time.time()
        logger.debug(
            f"获取或创建聊天会话: user_id={current_user.id}, agent_id={agent_id}"
        )
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        chat_session_time = time.time() - chat_session_start
        logger.debug(
            f"聊天会话获取成功: chat_id={chat.id}, agent_id={chat.agent_id}, 耗时: {chat_session_time:.3f}秒"
        )

        # 验证返回的chat中的agent_id是否与传入的一致
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: expected={agent_id}, actual={chat.agent_id}",
            )

        # 记录实际使用的agent_id
        logger.debug(f"实际聊天的Agent ID: {chat.agent_id}")

        # 获取最后一条用户消息
        msg_process_start = time.time()
        logger.debug(
            f"处理messages: {[f'{msg.role}: {msg.content[:50]}...' for msg in request.messages]}"
        )
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        logger.debug(f"找到的用户消息数量: {len(user_messages)}")
        if not user_messages:
            logger.error("请求中没有用户消息")
            logger.error(f"所有消息的role: {[msg.role for msg in request.messages]}")
            raise HTTPException(status_code=400, detail="No user message found")

        last_user_message = user_messages[-1].content
        logger.debug(f"用户消息: {last_user_message[:100]}...")

        # 构建LangChain消息格式
        messages = {"messages": [HumanMessage(content=last_user_message)]}
        msg_process_time = time.time() - msg_process_start
        logger.debug(f"消息处理耗时: {msg_process_time:.3f}秒")

        # 获取或创建Agent实例 - 需要加载完整数据
        agent_get_start = time.time()
        logger.debug(f"准备获取Agent实例: {chat.agent_id}")

        # 使用高性能的聊天专用Agent获取方法
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=chat.agent_id)
        if not agent_data:
            logger.error(f"Agent数据未找到: {chat.agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")

        # 从AgentManager缓存获取Agent实例
        agent = await agent_manager.get_agent(agent_data)
        agent_get_time = time.time() - agent_get_start
        logger.debug(
            f"Agent实例获取成功: {agent_data['name']}, 耗时: {agent_get_time:.3f}秒"
        )

        # 使用统一的session_id生成规则
        session_id_start = time.time()
        session_id = generate_session_id(chat.id)
        session_id_time = time.time() - session_id_start
        logger.debug(f"Session ID生成耗时: {session_id_time:.3f}秒")

        # 检查用户聊天次数限制
        is_allowed, used_count, daily_limit = (
            await subscription_service.check_chat_limit(db, current_user)
        )

        if not is_allowed:
            # 在返回错误前，先保存用户消息到聊天历史
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
        try:
            # 语音自动播放逻辑：chat_settings.voice_enabled = true 时自动生成语音
            if chat_settings.voice_enabled:
                # 使用Agent的voice_id字段
                agent_voice_id = agent_data.get("voice_id")
                logger.debug(
                    f"开始语音生成: voice_id={agent_voice_id}, text_length={len(response_content)}, language={request.language}"
                )

                audio_url = await voice_service.generate_voice(
                    text=response_content,
                    voice_id=agent_voice_id,
                    language=request.language,
                    db=db,
                )
                logger.debug(f"语音自动生成成功: {audio_url}")
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

        # 构建响应消息
        logger.debug("构建聊天响应消息")
        message = {"role": "assistant", "content": response_content}

        # 如果生成了语音，添加到响应中
        if audio_url:
            message["audio_url"] = audio_url
            logger.debug(f"响应包含语音URL: {audio_url}")

        total_request_time = time.time() - request_start_time
        logger.debug(
            f"聊天请求处理成功: agent_id={agent_id}, response_length={len(response_content)}, 总耗时: {total_request_time:.3f}秒"
        )
        data = {
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
        return schemas.APIResponse.success(data=data)

    except Exception as e:
        logger.error(f"聊天请求处理失败: {str(e)}")
        logger.exception("聊天请求异常详细信息:")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
