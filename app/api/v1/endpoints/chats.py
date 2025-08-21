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
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.chat import ChatCompletionRequest
from app.schemas.response import BusinessErrorCode, create_business_error_response
from app.services import agent_service, chat_history_service, chat_service
from app.services.async_voice_service import async_voice_service
from app.services.chat_service import generate_session_id
from app.services.subscription_service import subscription_service
from app.services.voice_cache_service import voice_cache_service
from app.services.voice_cleanup_service import voice_cleanup_service
from app.services.voice_service import voice_service

router = APIRouter(prefix="/chats", route_class=LoggerRoute)

logger = logging.getLogger(__name__)


@router.get("/", response_model=List[schemas.Chat])
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


@router.post("/", response_model=schemas.Chat)
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


@router.delete("/{chat_id}", response_model=schemas.Chat)
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


# OpenAI style message model
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = False
    model: str = "chatbot"
    language: str = "zh"  # 添加语言字段，默认中文


@router.get(
    "/agents/status",
    deprecated=True,
    include_in_schema=False,
    description="No record of who is using this",
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


@router.post(
    "/agents/initialize",
    deprecated=True,
    include_in_schema=False,
    description="No record of who is using this",
)
async def initialize_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Manually initialize commonly used Agents (admin function)
    """
    try:
        await agent_manager.initialize_popular_agents(db)
        return {
            "status": "success",
            "message": "Common Agents initialization completed",
            "active_agents": agent_manager.get_agent_count(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@router.delete(
    "/agents/cleanup",
    deprecated=True,
    include_in_schema=False,
    description="No record of who is using this",
)
async def cleanup_idle_agents(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Manually cleanup idle Agents (admin function)
    """
    try:
        old_count = agent_manager.get_agent_count()
        agent_manager._cleanup_idle_agents()
        new_count = agent_manager.get_agent_count()
        return {
            "status": "success",
            "message": "Idle Agents cleanup completed",
            "cleaned_count": old_count - new_count,
            "remaining_agents": new_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get(
    "/{chat_id}/detail",
    include_in_schema=False,
    tags=["unknown"],
    summary="Get Chat Detail",
    description="Get chat details with paginated message records",
)
async def get_chat_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="Number of messages per page"),
    offset: int = Query(0, ge=0, description="Offset (number of messages to skip)"),
) -> Any:
    """
    Get chat details with paginated message records
    Support scrolling to load earlier conversations
    """
    # Verify if chat exists
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Verify if chat belongs to current user
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        # Use unified session_id generation rule
        session_id = generate_session_id(chat_id)

        # Get paginated messages
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id, limit=limit, offset=offset
        )

        # Assemble return data
        return {
            "chat_info": {
                "id": chat.id,
                "agent_id": chat.agent_id,
                "agent_name": chat.agent_name,
                "agent_avatar": chat.agent_avatar,
                "user_id": chat.user_id,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
            },
            "messages": messages_data["messages"],
            "pagination": {
                "total": messages_data["total"],
                "limit": messages_data["limit"],
                "offset": messages_data["offset"],
                "page": messages_data["page"],
                "has_more": messages_data["has_more"],
                "total_pages": (
                    (messages_data["total"] + limit - 1) // limit if limit > 0 else 1
                ),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat details: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/detail",
    tags=["unknown", "inty-eval"],
    include_in_schema=False,
    deprecated=True,
    summary="Get Chat Detail for agent identified by agent_id",
    description="Return the chat details by Agent ID with paginated message records",
)
async def get_agent_chat_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="Number of messages per page"),
    offset: int = Query(0, ge=0, description="Offset (number of messages to skip)"),
) -> Any:
    """
    Get chat details by Agent ID with paginated message records
    If user hasn't created a session with this Agent, automatically create one
    Support scrolling to load earlier conversations
    """
    try:
        logger.info(f"Getting Agent chat details - Agent ID: {agent_id}")

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

        # Get paginated messages
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id, limit=limit, offset=offset
        )

        # Assemble return data
        data = {
            "chat_info": {
                "id": chat.id,
                "agent_id": chat.agent_id,
                "agent_name": chat.agent_name,
                "agent_avatar": chat.agent_avatar,
                "user_id": chat.user_id,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
            },
            "messages": messages_data["messages"],
            "pagination": {
                "total": messages_data["total"],
                "limit": messages_data["limit"],
                "offset": messages_data["offset"],
                "page": messages_data["page"],
                "has_more": messages_data["has_more"],
                "total_pages": (
                    (messages_data["total"] + limit - 1) // limit if limit > 0 else 1
                ),
            },
        }
        return data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat details: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/messages",
    tags=["inty-eval"],
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
) -> Any:
    """
    Get only chat message records by Agent ID (lighter interface)
    If user hasn't created a session with this Agent, automatically create one
    Specifically for scrolling load
    """
    try:
        logger.info(f"Getting Agent chat messages - Agent ID: {agent_id}")

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

        # 获取分页消息
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id, limit=limit, offset=offset
        )

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
    "/agents/{agent_id}/chat/completions",
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
    try:
        import time

        request_start_time = time.time()
        logger.info(
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
        logger.info(f"Agent验证成功: {agent_basic[1]}, 耗时: {agent_query_time:.3f}秒")
        # 添加日志记录传入的agent_id
        logger.info(f"请求的Agent ID: {agent_id}")

        # 获取或创建与该Agent的唯一会话
        chat_session_start = time.time()
        logger.debug(
            f"获取或创建聊天会话: user_id={current_user.id}, agent_id={agent_id}"
        )
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        chat_session_time = time.time() - chat_session_start
        logger.info(
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
        logger.info(f"实际聊天的Agent ID: {chat.agent_id}")

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
        logger.info(f"消息处理耗时: {msg_process_time:.3f}秒")

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
        logger.info(
            f"Agent实例获取成功: {agent_data['name']}, 耗时: {agent_get_time:.3f}秒"
        )

        # 使用统一的session_id生成规则
        session_id_start = time.time()
        session_id = generate_session_id(chat.id)
        session_id_time = time.time() - session_id_start
        logger.info(f"Session ID生成耗时: {session_id_time:.3f}秒")

        # 检查用户聊天次数限制
        is_allowed, used_count, daily_limit = (
            await subscription_service.check_chat_limit(db, current_user)
        )

        if not is_allowed:
            # 在返回错误前，先保存用户消息到聊天历史
            try:
                chat_history_service.add_user_message(session_id, last_user_message)
                logger.info(f"用户消息已保存到历史记录: {session_id}")
            except Exception as e:
                logger.warning(f"保存用户消息失败: {str(e)}")

            return create_business_error_response(
                error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED,
                extra_data={"used_count": used_count, "daily_limit": daily_limit},
            )

        if request.stream:
            logger.debug(f"开始流式聊天处理: session_id={session_id}")
            return StreamingResponse(
                generate_chat_stream(
                    agent=agent,
                    messages=messages,
                    user_id=current_user.id,
                    session_id=session_id,
                    chat_id=chat.id,
                    model_name=request.model,
                    db_session=db,
                    agent_id=agent_id,
                    last_user_message=last_user_message,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
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
                        db_session=db,
                        chat_settings=chat_settings,
                    )
                )

                # 等待任务完成
                response_content = await ai_task
                chat_processing_time = time.time() - chat_processing_start
                logger.info(
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
                    logger.info(
                        f"开始语音生成: voice_id={agent_voice_id}, text_length={len(response_content)}, language={request.language}"
                    )

                    audio_url = await voice_service.generate_voice(
                        text=response_content,
                        voice_id=agent_voice_id,
                        language=request.language,
                        db=db,
                    )
                    logger.info(f"语音自动生成成功: {audio_url}")
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
                logger.info(f"响应包含语音URL: {audio_url}")

            total_request_time = time.time() - request_start_time
            logger.info(
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


@router.post("/agents/{agent_id}/chat/fast", response_model=dict)
async def agent_chat_fast_response(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ChatCompletionRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    极速聊天响应接口
    立即返回AI文本回复，语音异步生成
    """
    try:
        logger.info(
            f"开始处理极速聊天请求 - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # 使用高性能的聊天专用Agent获取方法
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 获取或创建与该Agent的唯一会话
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        # 获取最后一条用户消息
        try:
            user_messages = [
                msg for msg in request.messages if getattr(msg, "role", None) == "user"
            ]
            logger.debug(f"找到的用户消息数量: {len(user_messages)}")
            if not user_messages:
                logger.error("请求中没有用户消息")
                logger.error(
                    f"所有消息的role: {[getattr(msg, 'role', 'unknown') for msg in request.messages]}"
                )
                raise HTTPException(status_code=400, detail="No user message found")

            last_user_message = user_messages[-1].content
            logger.debug(f"用户消息: {last_user_message[:100]}...")
        except Exception as e:
            logger.error(f"消息处理失败: {str(e)}")
            logger.error(f"消息类型: {type(request.messages)}")
            if request.messages:
                logger.error(f"第一个消息类型: {type(request.messages[0])}")
                logger.error(f"第一个消息内容: {request.messages[0]}")
            raise HTTPException(
                status_code=400, detail=f"Message processing failed: {str(e)}"
            )

        # 构建LangChain消息格式
        messages = {"messages": [HumanMessage(content=last_user_message)]}

        # 创建Agent实例（agent_data已从缓存获取）
        agent = await agent_manager.get_agent(agent_data)

        # 使用session_id
        session_id = generate_session_id(chat.id)

        # 先获取AI回复
        response_content = await agent.chat(
            user_id=current_user.id,
            session_id=session_id,
            messages=messages,
            db_session=None,  # Agent内部使用自己的连接池
        )

        # 然后获取聊天设置
        chat_settings = await chat_service.get_or_create_chat_settings(
            db, chat.id, current_user.id, agent_id
        )

        # 构建基础响应
        message = {"role": "assistant", "content": response_content}

        # 语音处理逻辑
        if chat_settings.voice_enabled:
            # 立即检查AI回复内容的缓存，使用独立的数据库会话
            cached_audio_url = await async_voice_service.check_cache_first(
                text=response_content,
                voice_id=agent_data.get("voice_id"),
                language=request.language,
                db=None,  # 使用独立的数据库会话
            )

            if cached_audio_url:
                # 缓存命中，立即返回
                message["audio_url"] = cached_audio_url
                message["audio_cached"] = True
                logger.info(f"极速响应-缓存命中: {cached_audio_url}")
            else:
                # 缓存未命中，启动异步生成
                task_id = await async_voice_service.generate_voice_async(
                    message_id=f"msg_{uuid.uuid4().hex[:8]}",
                    text=response_content,
                    voice_id=agent_data.get("voice_id"),
                    language=request.language,
                    db=None,  # 使用独立的数据库会话
                )

                message["audio_task_id"] = task_id
                message["audio_cached"] = False
                logger.info(f"极速响应-异步生成: {task_id}")

        # 异步记录使用情况，使用独立的数据库会话
        asyncio.create_task(
            subscription_service.record_usage(
                None,
                current_user.id,
                "chat",
                1,
                extra_data={
                    "agent_id": agent_id,
                    "message_length": len(last_user_message),
                },
            )
        )

        logger.info(
            f"极速聊天响应完成: agent_id={agent_id}, response_length={len(response_content)}"
        )

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": len(last_user_message),
                "completion_tokens": len(response_content),
                "total_tokens": len(last_user_message) + len(response_content),
            },
            "response_type": "fast",
            "voice_enabled": chat_settings.voice_enabled,
        }

    except Exception as e:
        logger.error(f"极速聊天请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fast chat failed: {str(e)}")


@router.get(
    "/voice/tasks/{task_id}",
    include_in_schema=False,
    tags=["inty", "voice"],
    summary="Get Voice Task Status",
    description="No record of who is using this",
)
async def get_voice_task_status(
    task_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取异步语音任务状态
    """
    try:
        task_status = await async_voice_service.get_task_status(task_id)

        if task_status["status"] == "not_found":
            detail = task_status.get("message", "Task not found")
            raise HTTPException(status_code=404, detail=detail)

        return task_status

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"获取语音任务状态失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get task status: {str(e)}"
        )


@router.get(
    "/voice/tasks/stats",
    include_in_schema=False,
    tags=["inty", "voice"],
    summary="Get Voice Task Stats",
    description="Get voice task stats",
)
async def get_voice_task_stats(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取语音任务统计信息
    """
    try:
        stats = async_voice_service.get_task_stats()
        return stats

    except Exception as e:
        logger.error(f"获取语音任务统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get task stats: {str(e)}"
        )


@router.post(
    "/agents/{agent_id}/messages/{message_id}/voice",
    include_in_schema=False,
    tags=["inty", "voice"],
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
            session_id=session_id, message_id=message_id
        )

        if not message_content:
            raise HTTPException(status_code=404, detail="Message not found")

        # 使用Agent的voice_id生成语音
        agent_voice_id = agent_data.get("voice_id")
        audio_url = await voice_service.generate_voice(
            text=message_content, voice_id=agent_voice_id, language=language, db=db
        )

        if not audio_url:
            raise HTTPException(status_code=500, detail="Voice generation failed")

        logger.info(f"按需语音生成成功: {audio_url}")

        return {
            "audio_url": audio_url,
            "message_id": message_id,
            "voice_id": agent_voice_id
            or global_config_loaded_from_config_yaml.elevenlabs.voice_id,
            "language": language,
            "cached": False,  # 这里可以后续实现缓存检测
            "generation_time": None,  # 可以记录生成时间
        }

    except Exception as e:
        logger.error(f"按需语音生成失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Voice generation failed: {str(e)}"
        )


@router.get(
    "/voices",
    include_in_schema=False,
    tags=["inty", "voice"],
    summary="Get Available Voices",
    description="Get available voices",
)
async def get_available_voices(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取可用的语音列表
    """
    try:
        voices = await voice_service.get_available_voices()
        return {
            "voices": voices,
            "default_voice_id": global_config_loaded_from_config_yaml.elevenlabs.voice_id,
        }
    except Exception as e:
        logger.error(f"获取语音列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get voices: {str(e)}")


@router.get(
    "/voices/{voice_id}",
    include_in_schema=False,
    tags=["inty", "voice"],
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


@router.post(
    "/voice/cleanup",
    include_in_schema=False,
    tags=["inty", "voice"],
    summary="Manual Voice Cleanup",
    description="Manual cleanup of voice files",
)
async def manual_voice_cleanup(
    cleanup_type: str = Query("all", description="清理类型: expired, invalid, all"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    手动执行语音文件清理
    """
    try:
        # 这里可以添加权限检查，只允许管理员执行
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="权限不足")

        result = await voice_cleanup_service.manual_cleanup(cleanup_type)
        return result

    except Exception as e:
        logger.error(f"手动清理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Manual cleanup failed: {str(e)}")


@router.get(
    "/voice/stats",
    include_in_schema=False,
    tags=["inty", "voice"],
    summary="Get Voice Stats",
    description="Get voice stats",
)
async def get_voice_stats(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取语音缓存统计信息
    """
    try:
        cleanup_stats = await voice_cleanup_service.get_cleanup_stats()
        return cleanup_stats

    except Exception as e:
        logger.error(f"获取语音统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get voice stats: {str(e)}"
        )


@router.get(
    "/voice/cache/stats",
    include_in_schema=False,
    tags=["inty", "voice"],
    summary="Get Voice Cache Stats",
    description="Get voice cache stats",
)
async def get_voice_cache_stats(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取语音缓存详细统计信息
    """
    try:
        cache_stats = await voice_cache_service.get_cache_stats(db)
        return cache_stats

    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache stats: {str(e)}"
        )


@router.put(
    "/agents/{agent_id}/settings",
    include_in_schema=False,
    tags=["inty"],
    summary="Update Agent Chat Settings",
    description="Update chat settings by Agent ID",
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

        # Check if trying to update style_prompt and if user has subscription
        if settings_update.style_prompt is not None:
            subscription_status = (
                await subscription_service.get_user_subscription_status(
                    db, current_user.id
                )
            )
            if not subscription_status.is_subscribed:
                return create_business_error_response(
                    error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED
                )

        # Check if trying to update premium_mode and if user has subscription
        if settings_update.premium_mode is not None and settings_update.premium_mode:
            subscription_status = (
                await subscription_service.get_user_subscription_status(
                    db, current_user.id
                )
            )
            if not subscription_status.is_subscribed:
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
    include_in_schema=False,
    tags=["inty"],
    summary="Get Agent Chat Settings",
    description="Get chat settings by Agent ID",
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
    include_in_schema=False,
    tags=["inty"],
    summary="Delete Agent Chats",
    description="Delete all chats by Agent ID",
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


@router.get(
    "/agents/{agent_id}/debug-messages",
    include_in_schema=False,
    tags=["inty-eval"],
    summary="Get Agent Debug Messages",
    description="Get Agent Debug Messages by Agent ID",
)
async def get_agent_debug_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取Agent对话的调试信息
    根据Agent ID获取用户与该Agent的聊天会话中的debug_messages字段
    """
    try:
        logger.info(
            f"获取Agent调试信息 - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # 首先验证Agent是否存在
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 获取用户与该Agent的聊天会话
        chat = await chat_service.get_chat_by_agent_and_user(
            db=db, agent_id=agent_id, user_id=current_user.id
        )

        if not chat:
            # 如果没有聊天会话，返回空的调试信息
            return {
                "chat_id": None,
                "agent_id": agent_id,
                "agent_name": agent_db.name,
                "debug_messages": None,
                "message": "No chat session found with this agent",
            }

        # 返回调试信息
        return {
            "chat_id": chat.id,
            "agent_id": chat.agent_id,
            "agent_name": chat.agent_name or agent_db.name,
            "debug_messages": chat.debug_messages,
            "last_updated": chat.updated_at.isoformat() if chat.updated_at else None,
            "message": (
                "Debug messages retrieved successfully"
                if chat.debug_messages
                else "No debug messages available"
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent调试信息失败 - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get debug messages: {str(e)}"
        )


async def generate_chat_stream(
    agent,
    messages: dict,
    user_id: str,
    session_id: str,
    chat_id: str,
    model_name: str,
    db_session: AsyncSession = None,
    agent_id: str = None,
    last_user_message: str = None,
):
    """
    Generate streaming chat response (async version)
    """
    try:
        # Use Agent's async chat_stream method
        async for message_chunk, metadata in agent.chat_stream(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            db_session=db_session,
        ):
            # Check message chunk type, only send AI messages
            if hasattr(message_chunk, "content") and message_chunk.content:
                chunk_data = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "content": message_chunk.content,
                            },
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

        # Send end marker
        end_chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Streaming chat failed: {str(e)}")
        error_chunk = {
            "error": {"message": f"Chat failed: {str(e)}", "type": "server_error"}
        }
        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"


@router.post(
    "/agents/{agent_id}/clear-messages",
    response_model=schemas.ClearMessagesResponse,
    include_in_schema=False,
    tags=["inty-eval"],
    summary="Clear Agent Chat Messages",
    description="Clear chat messages by Agent ID, currently used by inty-eval, probably will be used by inty app as well.",
)
async def clear_agent_chat_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: schemas.ClearMessagesRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    清除指定Agent聊天会话中的部分消息记录
    支持两种方式：
    1. 通过消息ID清除该ID之后的所有消息
    2. 通过时间戳清除该时间之后的所有消息
    """
    try:
        logger.info(
            f"清除Agent聊天消息 - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # 验证请求参数
        if not request.message_id and not request.timestamp:
            raise HTTPException(
                status_code=400, detail="必须提供 message_id 或 timestamp 中的一个参数"
            )

        if request.message_id and request.timestamp:
            raise HTTPException(
                status_code=400,
                detail="只能提供 message_id 或 timestamp 中的一个参数，不能同时提供",
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
            raise HTTPException(status_code=404, detail="未找到与该Agent的聊天会话")

        # 生成session_id
        session_id = generate_session_id(chat.id)

        # 执行清除操作
        if request.message_id is not None:
            # 按消息ID清除
            result = chat_history_service.clear_messages_after_id(
                session_id=session_id, message_id=request.message_id
            )
        else:
            # 按时间戳清除
            result = chat_history_service.clear_messages_after_timestamp(
                session_id=session_id, timestamp=request.timestamp
            )

        # 如果清除操作成功，同时清空 debug_messages 字段
        if result.get("success", False):
            chat.debug_messages = None
            await db.commit()
            logger.info(f"已清空 debug_messages 字段 - Chat ID: {chat.id}")

        logger.info(f"消息清除操作完成 - Agent ID: {agent_id}, 结果: {result}")

        return schemas.ClearMessagesResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除Agent聊天消息失败 - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to clear messages: {str(e)}"
        )


@router.get(
    "/debug-messages",
    description="Used by inty-eval to get chat history",
    tags=["inty-eval"],
    response_model=schemas.DebugMessageList,
    include_in_schema=False,
)
async def get_debug_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    user_id: Optional[str] = Query(None, description="用户ID"),
    agent_id: Optional[str] = Query(None, description="Agent ID"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=100, description="每页记录数"),
) -> Any:
    """
    查询debug messages
    支持按user_id和agent_id过滤，并支持分页
    如果两个参数都为空，则返回所有记录
    """
    try:
        logger.info(f"查询debug messages - user_id: {user_id}, agent_id: {agent_id}")

        # 调用service层方法查询debug messages
        result = await chat_service.get_debug_messages(
            db=db, user_id=user_id, agent_id=agent_id, skip=skip, limit=limit
        )

        logger.info(
            f"debug messages查询完成 - 总记录数: {result['total']}, "
            f"当前页记录数: {len(result['items'])}"
        )

        return schemas.DebugMessageList(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询debug messages失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to query debug messages: {str(e)}"
        )
