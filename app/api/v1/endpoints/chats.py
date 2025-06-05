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
from app.core.agent.agent import agent_manager
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.get("/", response_model=List[schemas.Chat])
async def list_chats(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户的聊天列表
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
    创建新的聊天
    """
    chat = await chat_service.create_chat(db, chat_in=chat_in, user_id=current_user.id)
    return chat

@router.get("/{chat_id}", response_model=schemas.Chat)
async def get_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    通过ID获取聊天
    """
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.put("/{chat_id}", response_model=schemas.Chat)
async def update_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    chat_in: schemas.ChatUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新聊天
    """
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat = await chat_service.update_chat(db, db_chat=chat, chat_in=chat_in)
    return chat

@router.delete("/{chat_id}", response_model=schemas.Chat)
async def delete_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除聊天
    """
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat = await chat_service.delete_chat(db, db_chat=chat)
    return chat


# OpenAI风格的消息模型
class ChatMessage(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = False
    model: str = "chatbot"


@router.post("/{chat_id}/chat/completions")
async def chat_completions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    request: ChatCompletionRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    OpenAI风格的聊天接口
    """
    # 验证聊天是否存在并获取关联的agent
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # 验证聊天是否属于当前用户
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # 获取Agent配置
    agent_db = await agent_service.get_agent(db, agent_id=chat.agent_id)
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        # 获取最后一条用户消息
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        last_user_message = user_messages[-1].content
        
        # 构建LangChain消息格式
        messages = {
            "messages": [HumanMessage(content=last_user_message)]
        }
        
        # 获取或创建Agent实例
        agent_data = {
            'id': agent_db.id,
            'name': agent_db.name,
            'prompt': agent_db.prompt,
            'settings': agent_db.settings
        }
        agent = await agent_manager.get_agent(agent_data)
        
        # 使用统一的session_id生成规则
        session_id = generate_session_id(chat_id)
        
        if request.stream:
            return StreamingResponse(
                generate_chat_stream(
                    agent=agent,
                    messages=messages,
                    user_id=current_user.id,
                    session_id=session_id,
                    chat_id=chat_id,
                    model_name=request.model
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # 非流式聊天
            response_content = agent.chat(
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
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")


async def generate_chat_stream(agent, messages: dict, user_id: str, session_id: str, chat_id: str, model_name: str):
    """生成流式聊天响应"""
    try:
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created_time = int(time.time())
        
        # 发送开始事件
        start_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(start_chunk, ensure_ascii=False)}\n\n"
        
        # 流式获取AI响应
        full_content = ""
        for message_chunk, metadata in agent.chat_stream(
            user_id=user_id,
            session_id=session_id,
            messages=messages
        ):
            if hasattr(message_chunk, 'content') and message_chunk.content:
                content = str(message_chunk.content)
                full_content += content
                
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        
        # 发送结束事件
        end_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_time,
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
        error_chunk = {
            "error": {
                "message": f"聊天失败: {str(e)}",
                "type": "server_error",
                "code": "internal_error"
            }
        }
        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"


@router.get("/agents/status")
async def get_agent_status(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取Agent管理器状态
    """
    return {
        "active_agents": agent_manager.get_agent_count(),
        "max_agents": agent_manager.max_agents,
        "cleanup_interval": agent_manager.cleanup_interval,
        "max_idle_time": agent_manager.max_idle_time
    }


@router.post("/agents/initialize")
async def initialize_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    手动初始化常用Agent（管理员功能）
    """
    try:
        await agent_manager.initialize_popular_agents(db)
        return {
            "status": "success",
            "message": "常用Agent初始化完成",
            "active_agents": agent_manager.get_agent_count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


@router.delete("/agents/cleanup")
async def cleanup_idle_agents(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    手动清理空闲Agent（管理员功能）
    """
    try:
        old_count = agent_manager.get_agent_count()
        agent_manager._cleanup_idle_agents()
        new_count = agent_manager.get_agent_count()
        return {
            "status": "success",
            "message": "空闲Agent清理完成",
            "cleaned_count": old_count - new_count,
            "remaining_agents": new_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/{chat_id}/detail")
async def get_chat_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="每页消息数量"),
    offset: int = Query(0, ge=0, description="偏移量（跳过的消息数量）"),
) -> Any:
    """
    获取对话详情，包含分页的消息记录
    支持滚屏加载更早的对话
    """
    # 验证聊天是否存在
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # 验证聊天是否属于当前用户
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        # 使用统一的session_id生成规则
        session_id = generate_session_id(chat_id)
        
        # 获取分页消息
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        # 组装返回数据
        return {
            "chat_info": {
                "id": chat.id,
                "agent_id": chat.agent_id,
                "agent_name": chat.agent_name,
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
        raise HTTPException(status_code=500, detail=f"获取对话详情失败: {str(e)}")


@router.get("/agents/{agent_id}/detail")
async def get_agent_chat_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="每页消息数量"),
    offset: int = Query(0, ge=0, description="偏移量（跳过的消息数量）"),
) -> Any:
    """
    根据Agent ID获取对话详情，包含分页的消息记录
    如果用户还没有和该Agent创建会话，则自动创建
    支持滚屏加载更早的对话
    """
    try:
        # 获取或创建与该Agent的唯一会话
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # 使用统一的session_id生成规则
        session_id = generate_session_id(chat.id)
        
        # 获取分页消息
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        # 组装返回数据
        return {
            "chat_info": {
                "id": chat.id,
                "agent_id": chat.agent_id,
                "agent_name": chat.agent_name,
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
        raise HTTPException(status_code=500, detail=f"获取对话详情失败: {str(e)}")


@router.get("/agents/{agent_id}/messages")
async def get_agent_chat_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="每页消息数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    order: str = Query("desc", regex="^(asc|desc)$", description="排序方式：asc=旧消息在前，desc=新消息在前"),
) -> Any:
    """
    根据Agent ID仅获取聊天消息记录（更轻量级的接口）
    如果用户还没有和该Agent创建会话，则自动创建
    专门用于滚动加载
    """
    try:
        # 获取或创建与该Agent的唯一会话
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # 使用统一的session_id生成规则
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
        raise HTTPException(status_code=500, detail=f"获取消息记录失败: {str(e)}")


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
        # 获取或创建与该Agent的唯一会话
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db,
            user_id=current_user.id,
            agent_id=agent_id
        )
        
        # 获取Agent配置
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # 获取最后一条用户消息
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        last_user_message = user_messages[-1].content
        
        # 构建LangChain消息格式
        messages = {
            "messages": [HumanMessage(content=last_user_message)]
        }
        
        # 获取或创建Agent实例
        agent_data = {
            'id': agent_db.id,
            'name': agent_db.name,
            'prompt': agent_db.prompt,
            'settings': agent_db.settings
        }
        agent = await agent_manager.get_agent(agent_data)
        
        # 使用统一的session_id生成规则
        session_id = generate_session_id(chat.id)
        
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
            # 非流式聊天
            response_content = agent.chat(
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
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}") 