import uuid
from typing import Any, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.core.chat import generate_chat_stream
from app.core.config import global_config_loaded_from_config_yaml
from app.core.user_privilege.premium_check import is_eligible_for_premium
from app.schemas.chat import ChatCompletionRequest
from app.schemas.response import BusinessErrorCode, create_business_error_response
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.global_services import subscription_service
from app.services.resource_service import delete_resource
from app.services.voice_service import voice_service

# TODO: Prefix should be /chat instead of /chats.
router = APIRouter(prefix="/chats", route_class=LoggerRoute)


@router.get(
    "/",
    response_model=List[schemas.Chat],
    summary="Get current user's chat list",
    description="Get current user's chat list",
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
    deprecated=True,
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
        logger.debug(f"Getting Agent chat details - Agent ID: {agent_id}")

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
    deprecated=True,
    include_in_schema=False,
    summary="用于支持 v1.0.3 app 新版 app 请勿使用本 API",
    description="基于Agent ID的OpenAI风格聊天接口，已弃用，请使用 /chat/completions/{agent_id} 代替",
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
    The following code is copied from tag:v1.0.3
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

        # 检查用户聊天次数限制
        # is_allowed, used_count, daily_limit = await subscription_service.check_chat_limit(
        #     db, current_user.id
        # )

        # if not is_allowed:
        #     raise HTTPException(
        #         status_code=429,  # Too Many Requests
        #         detail={
        #             "message": "今日聊天次数已达上限",
        #             "used_count": used_count,
        #             "daily_limit": daily_limit,
        #             "error_code": "CHAT_LIMIT_EXCEEDED"
        #         }
        #     )

        # 优化：简化Agent验证，在创建Agent实例时验证
        agent_query_start = time.time()
        logger.debug(f"简化Agent验证: {agent_id}")

        # 简化查询，只获取基本字段
        from sqlalchemy import select

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

        if request.stream:
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
            # 非流式聊天（异步）
            chat_processing_start = time.time()
            logger.debug(f"开始Agent聊天处理: session_id={session_id}")

            # 先获取聊天设置，再处理AI回复
            try:
                import asyncio

                # 先获取或创建聊天设置
                chat_settings = await chat_service.get_or_create_chat_settings(
                    db, chat.id, current_user.id, agent_id
                )

                # 然后处理AI回复
                response_content = await agent.chat(
                    user_id=current_user.id,
                    session_id=session_id,
                    messages=messages,
                )
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
                        logger.info(
                            f"语音自动生成成功: {audio_url}, 时长: {audio_duration:.2f}秒"
                        )
                    else:
                        audio_url, audio_duration = None, None
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
            message = {"role": "assistant", "content": response_content}

            # 如果生成了语音，添加到响应中
            if audio_url:
                message["audio_url"] = audio_url
                logger.info(f"响应包含语音URL: {audio_url}")

            # 获取最新AI消息的完整信息
            try:
                latest_message_info = (
                    await chat_history_service.get_latest_ai_message_info(
                        db, session_id
                    )
                )
            except Exception as e:
                logger.warning(f"获取最新消息信息失败: {str(e)}")
                latest_message_info = None

            # 添加消息的完整信息（id, meta_data, timestamp等）
            if latest_message_info:
                message["id"] = latest_message_info["id"]
                message["meta_data"] = latest_message_info["meta_data"]
                message["timestamp"] = latest_message_info["timestamp"]
                # 如果数据库中有audio_url，使用数据库的，否则使用新生成的
                if latest_message_info["audio_url"]:
                    message["audio_url"] = latest_message_info["audio_url"]

            total_request_time = time.time() - request_start_time

            # 构建符合客户端期望的响应格式 (HttpResult<SendMsgResponse>)
            response_data = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",  # 保持随机生成的外层ID
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

            logger.info(
                f"聊天请求处理成功: agent_id={agent_id}, 总耗时: {total_request_time:.3f}秒"
            )

            return response_data

    except Exception as e:
        logger.error(f"聊天请求处理失败: {str(e)}")
        logger.exception("聊天请求异常详细信息:")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post(
    "/agents/{agent_id}/messages/{message_id}/voice",
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

        return {
            "audio_url": audio_url,
            "message_id": message_id,
            "voice_id": agent_voice_id
            or global_config_loaded_from_config_yaml.elevenlabs.voice_id,
            "language": language,
            "audio_duration": audio_duration,  # 音频时长（秒）
            "cached": False,  # 这里可以后续实现缓存检测
            "generation_time": None,  # 可以记录生成时间
        }

    except Exception as e:
        logger.error(f"按需语音生成失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Voice generation failed: {str(e)}"
        )


@router.get(
    "/voices/{voice_id}",
    deprecated=True,
    include_in_schema=True,
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


@router.put(
    "/agents/{agent_id}/settings",
    tags=["inty"],
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
    tags=["inty"],
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
    tags=["inty"],
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


@router.get(
    "/agents/{agent_id}/debug-messages",
    deprecated=True,
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
        logger.debug(
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
            logger.debug(f"已清空 debug_messages 字段 - Chat ID: {chat.id}")

        logger.info(f"消息清除操作完成 - Agent ID: {agent_id}, 结果: {result}")

        return schemas.ClearMessagesResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除Agent聊天消息失败 - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to clear messages: {str(e)}"
        )
