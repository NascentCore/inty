from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
import time
from pydantic import BaseModel

from app import schemas
from app.api import deps
from app.services import chat_service, agent_service, chat_history_service
from app.services.chat_service import generate_session_id
from app.services.keep_talking_service import keep_talking_service
from app.core.agent.agent import agent_manager
from langchain_core.messages import HumanMessage
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/", response_model=List[schemas.Chat])
async def list_chats(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user's chat list
    """
    chats = await chat_service.get_chats(db, user_id=current_user.id, skip=skip, limit=limit)
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


@router.get("/agents/status")
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
        "max_idle_time": agent_manager.max_idle_time
    }


@router.get("/keep-talking/status")
async def get_keep_talking_status(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Get Keep Talking service status
    """
    return {
        "running": keep_talking_service._running,
        "check_interval": keep_talking_service.check_interval,
        "max_idle_time": keep_talking_service.max_idle_time,
        "max_keep_talking_messages": keep_talking_service.max_keep_talking_messages,
        "active_sessions_count": len(keep_talking_service._keep_talking_counts),
        "keep_talking_counts": keep_talking_service._keep_talking_counts
    }


@router.post("/keep-talking/check")
async def trigger_keep_talking_check(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Manually trigger Keep Talking check (for testing and debugging)
    """
    try:
        await keep_talking_service._check_idle_chats()
        return {
            "status": "success",
            "message": "Keep Talking check completed",
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")


@router.post("/agents/initialize")
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
            "active_agents": agent_manager.get_agent_count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@router.delete("/agents/cleanup")
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
            "remaining_agents": new_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/{chat_id}/detail")
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
            session_id=session_id,
            limit=limit,
            offset=offset
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
                "total_pages": (messages_data["total"] + limit - 1) // limit if limit > 0 else 1
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat details: {str(e)}")


@router.get("/agents/{agent_id}/detail")
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
            db=db,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
        
        # Use unified session_id generation rule
        session_id = generate_session_id(chat.id)
        
        # Get paginated messages
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id,
            limit=limit,
            offset=offset
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
                "total_pages": (messages_data["total"] + limit - 1) // limit if limit > 0 else 1
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat details: {str(e)}")


@router.get("/agents/{agent_id}/messages")
async def get_agent_chat_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="Number of messages per page"),
    offset: int = Query(0, ge=0, description="Offset"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order: asc=old messages first, desc=new messages first"),
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
            db=db,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
        
        # Use unified session_id generation rule
        session_id = generate_session_id(chat.id)
        
        # 获取分页消息
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        # 如果要求升序（旧消息在前），则不反转
        # 如果要求降序（新消息在前），则反转消息列表
        if order == "desc":
            messages_data["messages"].reverse()
        
        return messages_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get message records: {str(e)}")


@router.post("/agents/{agent_id}/chat/completions")
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
        # 首先验证Agent是否存在
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # 添加日志记录传入的agent_id
        logger.info(f"请求的Agent ID: {agent_id}")
        
        # 获取或创建与该Agent的唯一会话
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # 验证返回的chat中的agent_id是否与传入的一致
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}")
        
        # 记录实际使用的agent_id
        logger.info(f"实际聊天的Agent ID: {chat.agent_id}")
        
        # 获取最后一条用户消息
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        last_user_message = user_messages[-1].content
        
        # 构建LangChain消息格式
        messages = {
            "messages": [HumanMessage(content=last_user_message)]
        }
        
        # 获取或创建Agent实例 - 使用chat中的agent_id确保一致性
        agent_data = {
            'id': chat.agent_id,  # 使用chat中的agent_id而不是传入的agent_id
            'name': agent_db.name,
            'prompt': agent_db.prompt,
            'settings': agent_db.settings
        }
        agent = await agent_manager.get_agent(agent_data)
        
        # 使用统一的session_id生成规则
        session_id = generate_session_id(chat.id)
        
        # 用户发送新消息时，重置keep_talking计数
        keep_talking_service.reset_keep_talking_count(chat.id)
        logger.debug(f"重置会话 {chat.id} 的keep_talking计数")
        
        if request.stream:
            return StreamingResponse(
                generate_chat_stream(
                    agent=agent,
                    messages=messages,
                    user_id=current_user.id,
                    session_id=session_id,
                    chat_id=chat.id,
                    model_name=request.model
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # 非流式聊天（异步）
            response_content = await agent.chat(
                user_id=current_user.id,
                session_id=session_id,
                messages=messages
            )
            
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_content
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": len(last_user_message.split()),
                    "completion_tokens": len(response_content.split()),
                    "total_tokens": len(last_user_message.split()) + len(response_content.split())
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.put("/agents/{agent_id}/settings", response_model=schemas.ChatSettings)
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
        logger.info(f"Updating Agent chat settings - Agent ID: {agent_id}, User ID: {current_user.id}")
        
        # First verify if Agent exists
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"Agent ID mismatch")
        
        # Get or create chat settings, then update
        # First ensure settings exist
        settings = await chat_service.get_or_create_chat_settings(
            db=db,
            chat_id=chat.id,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # Then update settings
        settings = await chat_service.update_chat_settings(
            db=db,
            chat_id=chat.id,
            settings_update=settings_update
        )
        
        logger.info(f"Successfully updated Agent chat settings - Agent ID: {agent_id}, Settings ID: {settings.id}")
        
        return settings
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update Agent chat settings - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update chat settings: {str(e)}")


@router.get("/agents/{agent_id}/settings", response_model=schemas.ChatSettings)
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
        logger.info(f"Getting Agent chat settings - Agent ID: {agent_id}, User ID: {current_user.id}")
        
        # First verify if Agent exists
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # Get or create chat settings
        settings = await chat_service.get_or_create_chat_settings(
            db=db,
            chat_id=chat.id,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        logger.info(f"Successfully got Agent chat settings - Agent ID: {agent_id}, Settings ID: {settings.id}")
        
        return settings
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Agent chat settings - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat settings: {str(e)}")


async def generate_chat_stream(
    agent,
    messages: dict,
    user_id: str,
    session_id: str,
    chat_id: str,
    model_name: str
):
    """
    Generate streaming chat response (async version)
    """
    try:
        # Use Agent's async chat_stream method
        async for message_chunk, metadata in agent.chat_stream(
            user_id=user_id,
            session_id=session_id,
            messages=messages
        ):
            # Check message chunk type, only send AI messages
            if hasattr(message_chunk, 'content') and message_chunk.content:
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
                                "content": message_chunk.content
                            },
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
        
        # Send end marker
        end_chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Streaming chat failed: {str(e)}")
        error_chunk = {
            "error": {
                "message": f"Chat failed: {str(e)}",
                "type": "server_error"
            }
        }
        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n" 