from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
import logging
import uuid
import json

from app import models, schemas
from app.services import chat_history_service
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

def generate_session_id(chat_id: str) -> str:
    """
    Generate consistent session_id based on chat_id
    Ensure the same session_id is used when creating chat and chatting
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))

async def get_chat(db: AsyncSession, chat_id: str) -> Optional[models.Chat]:
    """
    Get chat by ID
    """
    try:
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings),
                selectinload(models.Chat.agent)
            )
            .where(models.Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        if chat:
            # Get recent message and timestamp, use unified session_id generation rule
            try:
                session_id = generate_session_id(chat.id)
                last_message_data = chat_history_service.get_last_message_with_timestamp(session_id)
                
                if last_message_data:
                    chat.last_message = last_message_data['content']
                    chat.last_message_time = last_message_data['timestamp']
                else:
                    chat.last_message = None
                    chat.last_message_time = None
            except Exception as e:
                logger.error(f"Failed to get recent message: {str(e)}")
                chat.last_message = None
                chat.last_message_time = None
            # Set agent name and avatar
            chat.agent_name = chat.agent.name if chat.agent else None
            chat.agent_avatar = chat.agent.avatar if chat.agent else None
        return chat
    except SQLAlchemyError as e:
        logger.error(f"Database query error - get chat {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unknown error - get chat {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def get_chats(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
) -> List[models.Chat]:
    """
    Get user's chat list, sorted by recent message time in descending order
    """
    try:
        # Validate parameters
        if skip < 0:
            raise HTTPException(status_code=400, detail="Skip parameter cannot be negative")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="Limit parameter must be between 1-1000")
            
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings),
                selectinload(models.Chat.agent)
            )
            .where(models.Chat.user_id == user_id)
        )
        all_chats = result.scalars().all()
        
        # Get recent message and timestamp for each chat
        chats_with_message_time = []
        for chat in all_chats:
            try:
                # Use unified session_id generation rule
                session_id = generate_session_id(chat.id)
                last_message_data = chat_history_service.get_last_message_with_timestamp(session_id)
                
                if last_message_data:
                    chat.last_message = last_message_data['content']
                    chat.last_message_time = last_message_data['timestamp']
                else:
                    chat.last_message = None
                    chat.last_message_time = None
                    
            except Exception as e:
                logger.error(f"Failed to get recent message: {str(e)}")
                chat.last_message = None
                chat.last_message_time = None
                
            chat.agent_name = chat.agent.name if chat.agent else None
            chat.agent_avatar = chat.agent.avatar if chat.agent else None
            chats_with_message_time.append(chat)
        
        # Sort by recent message time (chats without messages go last, sorted by creation time)
        chats_with_message_time.sort(
            key=lambda x: x.last_message_time if x.last_message_time else x.created_at,
            reverse=True
        )
        
        # Apply pagination
        return chats_with_message_time[skip:skip + limit]
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database query error - get user chat list: {str(e)}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unknown error - get user chat list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_chat(
    db: AsyncSession, chat_in: schemas.ChatCreate, user_id: str
) -> models.Chat:
    """
    Create new chat
    """
    try:
        # Generate unique ID
        chat_id = str(uuid.uuid4())
        
        # First get Agent's opening message
        agent_result = await db.execute(
            select(models.Agent)
            .where(models.Agent.id == chat_in.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        db_chat = models.Chat(
            id=chat_id,
            **chat_in.dict(),
            user_id=user_id
        )
        
        db.add(db_chat)
        await db.commit()
        await db.refresh(db_chat)
        
        # Add Agent opening message to chat_history, use unified session_id generation rule
        if agent.opening:
            try:
                session_id = generate_session_id(chat_id)
                chat_history_service.add_agent_opening_message(session_id, agent.opening)
            except Exception as e:
                logger.error(f"Failed to add opening message: {str(e)}")
                # Continue execution, don't affect chat creation
        
        # Re-query to load relational data
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings),
                selectinload(models.Chat.agent)
            )
            .where(models.Chat.id == db_chat.id)
        )
        chat = result.scalar_one()
        
        # Get recent message and timestamp (should be the opening message just added) and agent name
        try:
            session_id = generate_session_id(chat.id)
            last_message_data = chat_history_service.get_last_message_with_timestamp(session_id)
            
            if last_message_data:
                chat.last_message = last_message_data['content']
                chat.last_message_time = last_message_data['timestamp']
            else:
                chat.last_message = None
                chat.last_message_time = None
        except Exception as e:
            logger.error(f"Failed to get recent message: {str(e)}")
            chat.last_message = None
            chat.last_message_time = None
        chat.agent_name = chat.agent.name if chat.agent else None
        chat.agent_avatar = chat.agent.avatar if chat.agent else None
        
        return chat
        
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Data integrity error - create chat: {str(e)}")
        if "user_id" in str(e):
            raise HTTPException(status_code=400, detail="Invalid user ID")
        elif "agent_id" in str(e):
            raise HTTPException(status_code=400, detail="Invalid Agent ID")
        else:
            raise HTTPException(status_code=400, detail="Data integrity constraint violation")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error - create chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unknown error - create chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def update_chat(
    db: AsyncSession,
    *,
    db_chat: models.Chat,
    chat_in: schemas.ChatUpdate
) -> models.Chat:
    """
    更新聊天
    """
    try:
        if not db_chat:
            raise HTTPException(status_code=404, detail="聊天不存在")
            
        update_data = chat_in.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")
            
        for field, value in update_data.items():
            setattr(db_chat, field, value)
            
        await db.commit()
        await db.refresh(db_chat)
        return db_chat
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"数据完整性错误 - 更新聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=400, detail="数据完整性约束违反")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 更新聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 更新聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def delete_chat(
    db: AsyncSession,
    *,
    db_chat: models.Chat
) -> models.Chat:
    """
    删除聊天
    """
    try:
        if not db_chat:
            raise HTTPException(status_code=404, detail="聊天不存在")
            
        await db.delete(db_chat)
        await db.commit()
        return db_chat
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"数据完整性错误 - 删除聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=400, detail="无法删除聊天，存在关联数据")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 删除聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 删除聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def get_or_create_chat_by_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> models.Chat:
    """
    根据用户ID和Agent ID获取或创建唯一的聊天会话（高性能优化版）
    每个用户和每个Agent只能有一个会话
    """
    try:
        logger.info(f"获取或创建聊天会话 - 用户ID: {user_id}, Agent ID: {agent_id}")
        
        # 1. 先检查会话缓存
        session_key = f"{user_id}:{agent_id}"
        cached_session = cache_service.get_session_info(session_key)
        if cached_session:
            logger.debug(f"从缓存获取聊天会话: {cached_session['chat_id']}")
            # 从缓存构建Chat对象
            chat = models.Chat(
                id=cached_session['chat_id'],
                user_id=user_id,
                agent_id=agent_id,
                is_active=True,
                created_at=cached_session.get('created_at'),
                updated_at=cached_session.get('updated_at')
            )
            chat.agent_name = cached_session.get('agent_name')
            chat.agent_avatar = cached_session.get('agent_avatar')
            return chat
        
        # 2. 数据库查询（使用简单查询，减少预加载）
        result = await db.execute(
            select(models.Chat)
            .where(
                models.Chat.user_id == user_id,
                models.Chat.agent_id == agent_id,
                models.Chat.is_active == True
            )
        )
        existing_chat = result.scalar_one_or_none()
        
        if existing_chat:
            logger.info(f"找到已存在的聊天会话 - Chat ID: {existing_chat.id}, Agent ID: {existing_chat.agent_id}")
            
            # 验证agent_id的一致性
            if existing_chat.agent_id != agent_id:
                logger.error(f"聊天会话中的Agent ID不匹配！期望: {agent_id}, 实际: {existing_chat.agent_id}")
                raise HTTPException(status_code=500, detail=f"聊天会话数据不一致: 期望Agent ID {agent_id}, 实际 {existing_chat.agent_id}")
            
            # 3. 并行获取Agent信息（如果未缓存）
            if not hasattr(existing_chat, '_agent_loaded'):
                # 从Agent缓存获取
                cached_agent = cache_service.get_agent_config(agent_id)
                if cached_agent:
                    existing_chat.agent_name = cached_agent.get('name')
                    existing_chat.agent_avatar = cached_agent.get('avatar')
                else:
                    # 数据库查询Agent信息
                    agent_result = await db.execute(
                        select(models.Agent.name, models.Agent.avatar)
                        .where(models.Agent.id == agent_id)
                    )
                    agent_info = agent_result.first()
                    if agent_info:
                        existing_chat.agent_name = agent_info[0]
                        existing_chat.agent_avatar = agent_info[1]
                        # 缓存Agent信息
                        cache_service.set_agent_config(agent_id, {
                            'name': agent_info[0],
                            'avatar': agent_info[1]
                        })
                    else:
                        existing_chat.agent_name = None
                        existing_chat.agent_avatar = None
                existing_chat._agent_loaded = True
            
            # 4. 缓存会话信息
            session_data = {
                'chat_id': existing_chat.id,
                'user_id': user_id,
                'agent_id': agent_id,
                'agent_name': getattr(existing_chat, 'agent_name', None),
                'agent_avatar': getattr(existing_chat, 'agent_avatar', None),
                'created_at': existing_chat.created_at,
                'updated_at': existing_chat.updated_at
            }
            cache_service.set_session_info(session_key, session_data)
            
            # 跳过last_message查询以提升性能（可在需要时单独查询）
            existing_chat.last_message = None
            existing_chat.last_message_time = None
            
            return existing_chat
        
        # 5. 如果不存在，则创建新的会话
        logger.info(f"未找到已存在的聊天会话，创建新的会话 - Agent ID: {agent_id}")
        
        # 6. 优先从缓存获取Agent信息
        cached_agent = cache_service.get_agent_config(agent_id)
        if cached_agent:
            agent_name = cached_agent.get('name')
            agent_avatar = cached_agent.get('avatar')
            agent_opening = cached_agent.get('opening')
            logger.debug(f"从缓存获取Agent信息: {agent_name}")
        else:
            # 数据库查询Agent信息
            agent_result = await db.execute(
                select(models.Agent.name, models.Agent.avatar, models.Agent.opening)
                .where(models.Agent.id == agent_id)
            )
            agent_info = agent_result.first()
            if not agent_info:
                logger.error(f"Agent不存在: {agent_id}")
                raise HTTPException(status_code=404, detail="Agent不存在")
            
            agent_name, agent_avatar, agent_opening = agent_info
            # 缓存Agent信息
            cache_service.set_agent_config(agent_id, {
                'name': agent_name,
                'avatar': agent_avatar,
                'opening': agent_opening
            })
            logger.info(f"验证Agent存在 - Agent ID: {agent_id}, Name: {agent_name}")
        
        # 7. 创建新的聊天会话
        chat_id = str(uuid.uuid4())
        db_chat = models.Chat(
            id=chat_id,
            user_id=user_id,
            agent_id=agent_id
        )
        
        logger.info(f"创建新聊天会话 - Chat ID: {chat_id}, User ID: {user_id}, Agent ID: {agent_id}")
        
        db.add(db_chat)
        await db.commit()
        await db.refresh(db_chat)
        
        # 验证创建后的agent_id
        if db_chat.agent_id != agent_id:
            logger.error(f"创建聊天会话后Agent ID不匹配！期望: {agent_id}, 实际: {db_chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"创建聊天会话失败: Agent ID不匹配")
        
        # 8. 异步添加Agent开场白（避免阻塞）
        if agent_opening:
            try:
                session_id = generate_session_id(chat_id)
                # 直接添加开场白，但简化处理避免长时间阻塞
                chat_history_service.add_agent_opening_message(session_id, agent_opening)
                logger.info(f"添加Agent开场白成功 - Session ID: {session_id}")
            except Exception as e:
                logger.error(f"提交开场白添加任务失败: {str(e)}")
                # 继续执行，不影响chat创建
        
        # 9. 设置Agent信息并缓存会话（优化：避免重复查询）
        db_chat.agent_name = agent_name
        db_chat.agent_avatar = agent_avatar
        
        # 10. 缓存新建的会话信息
        session_data = {
            'chat_id': db_chat.id,
            'user_id': user_id,
            'agent_id': agent_id,
            'agent_name': agent_name,
            'agent_avatar': agent_avatar,
            'created_at': db_chat.created_at,
            'updated_at': db_chat.updated_at
        }
        cache_service.set_session_info(session_key, session_data)
        
        # 11. 设置默认值（跳过耗时的消息查询）
        db_chat.last_message = None
        db_chat.last_message_time = None
        
        logger.info(f"成功创建新聊天会话 - Chat ID: {db_chat.id}, Agent ID: {db_chat.agent_id}")
        return db_chat
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"数据完整性错误 - 获取或创建聊天: {str(e)}")
        # 可能是并发创建导致的重复，尝试再次查询
        try:
            result = await db.execute(
                select(models.Chat)
                .options(
                    selectinload(models.Chat.settings),
                    selectinload(models.Chat.agent)
                )
                .where(
                    models.Chat.user_id == user_id,
                    models.Chat.agent_id == agent_id,
                    models.Chat.is_active == True
                )
            )
            existing_chat = result.scalar_one_or_none()
            if existing_chat:
                logger.info(f"并发创建冲突，返回已存在的聊天会话 - Chat ID: {existing_chat.id}")
                return existing_chat
        except Exception as retry_e:
            logger.error(f"重试查询失败: {str(retry_e)}")
            pass
        raise HTTPException(status_code=500, detail="创建聊天会话失败")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 获取或创建聊天: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 获取或创建聊天: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def get_or_create_chat_settings(
    db: AsyncSession, chat_id: str, user_id: str, agent_id: str
) -> models.ChatSettings:
    """
    获取或创建聊天设置
    """
    try:
        # 先查找是否已存在设置，预加载agent关系
        result = await db.execute(
            select(models.ChatSettings)
            .options(selectinload(models.ChatSettings.agent))
            .where(models.ChatSettings.chat_id == chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if settings:
            return settings
        
        # 如果不存在，创建新的设置
        settings_id = str(uuid.uuid4())
        db_settings = models.ChatSettings(
            id=settings_id,
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            language="zh",  # 默认中文
            voice_enabled=False,  # 默认不启用语音自动播放
            keep_talking=True
        )
        
        db.add(db_settings)
        await db.commit()
        await db.refresh(db_settings)
        
        # 重新查询以加载关系数据
        result = await db.execute(
            select(models.ChatSettings)
            .options(selectinload(models.ChatSettings.agent))
            .where(models.ChatSettings.id == db_settings.id)
        )
        settings_with_agent = result.scalar_one()
        
        return settings_with_agent
        
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 获取或创建聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 获取或创建聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def update_chat_settings(
    db: AsyncSession,
    chat_id: str,
    settings_update: schemas.ChatSettingsUpdate
) -> models.ChatSettings:
    """
    根据chat_id更新聊天设置
    """
    try:
        # 查找现有设置，预加载agent关系
        result = await db.execute(
            select(models.ChatSettings)
            .options(selectinload(models.ChatSettings.agent))
            .where(models.ChatSettings.chat_id == chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            raise HTTPException(status_code=404, detail="聊天设置不存在")
        
        # 更新设置
        update_data = settings_update.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")
            
        for field, value in update_data.items():
            setattr(settings, field, value)
            
        await db.commit()
        await db.refresh(settings)
        
        # 重新查询以确保关系数据已加载
        result = await db.execute(
            select(models.ChatSettings)
            .options(selectinload(models.ChatSettings.agent))
            .where(models.ChatSettings.id == settings.id)
        )
        updated_settings = result.scalar_one()
        
        return updated_settings
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 更新聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 更新聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def get_chat_by_agent_and_user(
    db: AsyncSession, agent_id: str, user_id: str
) -> Optional[models.Chat]:
    """
    根据agent_id和user_id获取唯一的聊天会话
    """
    try:
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings),
                selectinload(models.Chat.agent)
            )
            .where(
                models.Chat.agent_id == agent_id,
                models.Chat.user_id == user_id,
                models.Chat.is_active == True
            )
        )
        return result.scalar_one_or_none()
        
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取聊天会话 agent_id={agent_id}, user_id={user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取聊天会话 agent_id={agent_id}, user_id={user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def get_chat_by_user_and_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> Optional[models.Chat]:
    """
    根据user_id和agent_id获取唯一的聊天会话
    """
    return await get_chat_by_agent_and_user(db, agent_id, user_id) 

async def delete_chats_by_agent_id(
    db: AsyncSession,
    agent_id: str,
    user_id: str
) -> dict:
    """
    删除用户与指定agent的所有聊天记录
    
    Args:
        db: 数据库会话
        agent_id: Agent ID
        user_id: 用户ID
        
    Returns:
        dict: 删除结果摘要
    """
    try:
        logger.info(f"开始删除聊天记录 - Agent ID: {agent_id}, User ID: {user_id}")
        
        # 查找所有匹配的聊天记录
        result = await db.execute(
            select(models.Chat)
            .where(
                models.Chat.agent_id == agent_id,
                models.Chat.user_id == user_id
            )
        )
        chats = result.scalars().all()
        
        if not chats:
            logger.info(f"未找到聊天记录 - Agent ID: {agent_id}, User ID: {user_id}")
            return {
                "chats_deleted": 0,
                "messages_deleted": 0,
                "agent_id": agent_id,
                "user_id": user_id,
                "status": "no_chats_found"
            }
        
        deleted_chats_count = len(chats)
        total_messages_deleted = 0
        
        # 开始事务删除
        for chat in chats:
            try:
                # 生成session_id并删除聊天历史
                session_id = generate_session_id(chat.id)
                
                # 统计消息数量（在删除前）
                try:
                    messages_data = chat_history_service.get_messages_paginated(
                        session_id=session_id,
                        limit=1000,  # 获取所有消息进行计数
                        offset=0
                    )
                    message_count = messages_data.get("total", 0)
                    total_messages_deleted += message_count
                    
                    # 删除聊天历史
                    chat_history_service.clear_session(session_id)
                    logger.debug(f"已删除聊天历史 - Chat ID: {chat.id}, Session ID: {session_id}, 消息数: {message_count}")
                    
                except Exception as e:
                    logger.warning(f"删除聊天历史失败 - Chat ID: {chat.id}, Error: {str(e)}")
                    # 继续删除数据库记录，即使聊天历史删除失败
                
                # 删除数据库中的聊天记录（会级联删除chat_settings）
                await db.delete(chat)
                logger.debug(f"已删除聊天记录 - Chat ID: {chat.id}")
                
            except Exception as e:
                logger.error(f"删除单个聊天记录失败 - Chat ID: {chat.id}, Error: {str(e)}")
                # 继续处理其他聊天记录
                continue
        
        # 提交事务
        await db.commit()
        
        logger.info(f"聊天记录删除完成 - Agent ID: {agent_id}, User ID: {user_id}, "
                   f"删除聊天数: {deleted_chats_count}, 删除消息数: {total_messages_deleted}")
        
        return {
            "chats_deleted": deleted_chats_count,
            "messages_deleted": total_messages_deleted,
            "agent_id": agent_id,
            "user_id": user_id,
            "status": "success"
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"删除聊天记录失败 - Agent ID: {agent_id}, User ID: {user_id}, Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除聊天记录失败: {str(e)}")

async def save_debug_messages(
    db: AsyncSession,
    session_id: str,
    messages: List[dict]
) -> None:
    """
    保存调试信息到数据库
    
    Args:
        db: 数据库会话
        session_id: 会话ID
        messages: 要保存的消息列表
    """
    try:
        # 根据 session_id 推算出 chat_id
        # session_id 是通过 generate_session_id(chat_id) 生成的
        # 需要通过查询数据库找到对应的 chat 记录
        from app.core.config import settings
        
        # 如果调试功能未启用，直接返回
        if not settings.app.debug_messages:
            return
            
        # 查找对应的 chat 记录
        # 这里需要通过遍历来找到对应的 chat（因为 session_id 是基于 chat_id 生成的）
        result = await db.execute(select(models.Chat))
        chats = result.scalars().all()
        
        target_chat = None
        for chat in chats:
            if generate_session_id(chat.id) == session_id:
                target_chat = chat
                break
                
        if not target_chat:
            logger.warning(f"未找到对应的 chat 记录，session_id: {session_id}")
            return
            
        # 将消息列表转换为 JSON 格式并保存
        # 需要处理消息对象，确保它们可以被序列化
        serializable_messages = []
        for msg in messages:
            if hasattr(msg, 'dict'):
                # 如果是 Pydantic 模型或类似对象
                serializable_messages.append(msg.dict())
            elif hasattr(msg, '__dict__'):
                # 如果是普通对象
                serializable_messages.append(msg.__dict__)
            else:
                # 如果已经是字典
                serializable_messages.append(msg)
                
        target_chat.debug_messages = serializable_messages
        
        await db.commit()
        logger.debug(f"成功保存调试信息，session_id: {session_id}, 消息数量: {len(messages)}")
        
    except Exception as e:
        logger.error(f"保存调试信息失败，session_id: {session_id}, 错误: {str(e)}")
        await db.rollback()
        # 不抛出异常，避免影响正常的聊天流程 