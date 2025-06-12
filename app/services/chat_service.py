from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
import logging
import uuid

from app import models, schemas
from app.services import chat_history_service

logger = logging.getLogger(__name__)

def generate_session_id(chat_id: str) -> str:
    """
    根据chat_id生成一致的session_id
    确保在创建chat和聊天时使用相同的session_id
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))

async def get_chat(db: AsyncSession, chat_id: str) -> Optional[models.Chat]:
    """
    通过ID获取聊天
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
            # 获取最近消息和时间戳，使用统一的session_id生成规则
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
                logger.error(f"获取最近消息失败: {str(e)}")
                chat.last_message = None
                chat.last_message_time = None
            # 设置agent名称和头像
            chat.agent_name = chat.agent.name if chat.agent else None
            chat.agent_avatar = chat.agent.avatar if chat.agent else None
        return chat
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取聊天 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取聊天 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def get_chats(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
) -> List[models.Chat]:
    """
    获取用户的聊天列表，按最近消息时间降序排列
    """
    try:
        # 验证参数
        if skip < 0:
            raise HTTPException(status_code=400, detail="skip参数不能为负数")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="limit参数必须在1-1000之间")
            
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings),
                selectinload(models.Chat.agent)
            )
            .where(models.Chat.user_id == user_id)
        )
        all_chats = result.scalars().all()
        
        # 为每个chat获取最近消息和时间戳
        chats_with_message_time = []
        for chat in all_chats:
            try:
                # 使用统一的session_id生成规则
                session_id = generate_session_id(chat.id)
                last_message_data = chat_history_service.get_last_message_with_timestamp(session_id)
                
                if last_message_data:
                    chat.last_message = last_message_data['content']
                    chat.last_message_time = last_message_data['timestamp']
                else:
                    chat.last_message = None
                    chat.last_message_time = None
                    
            except Exception as e:
                logger.error(f"获取最近消息失败: {str(e)}")
                chat.last_message = None
                chat.last_message_time = None
                
            chat.agent_name = chat.agent.name if chat.agent else None
            chat.agent_avatar = chat.agent.avatar if chat.agent else None
            chats_with_message_time.append(chat)
        
        # 根据最近消息时间排序（没有消息的聊天放在最后，按创建时间排列）
        chats_with_message_time.sort(
            key=lambda x: x.last_message_time if x.last_message_time else x.created_at,
            reverse=True
        )
        
        # 应用分页
        return chats_with_message_time[skip:skip + limit]
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取用户聊天列表: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取用户聊天列表: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def create_chat(
    db: AsyncSession, chat_in: schemas.ChatCreate, user_id: str
) -> models.Chat:
    """
    创建新的聊天
    """
    try:
        # 生成唯一ID
        chat_id = str(uuid.uuid4())
        
        # 首先获取Agent的开场白
        agent_result = await db.execute(
            select(models.Agent)
            .where(models.Agent.id == chat_in.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent不存在")
        
        db_chat = models.Chat(
            id=chat_id,
            **chat_in.dict(),
            user_id=user_id
        )
        
        db.add(db_chat)
        await db.commit()
        await db.refresh(db_chat)
        
        # 添加Agent开场白到chat_history，使用统一的session_id生成规则
        if agent.opening:
            try:
                session_id = generate_session_id(chat_id)
                chat_history_service.add_agent_opening_message(session_id, agent.opening)
            except Exception as e:
                logger.error(f"添加开场白失败: {str(e)}")
                # 继续执行，不影响chat创建
        
        # 重新查询以加载关系数据
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings),
                selectinload(models.Chat.agent)
            )
            .where(models.Chat.id == db_chat.id)
        )
        chat = result.scalar_one()
        
        # 获取最近消息和时间戳 (应该是刚添加的开场白) 和agent名称
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
            logger.error(f"获取最近消息失败: {str(e)}")
            chat.last_message = None
            chat.last_message_time = None
        chat.agent_name = chat.agent.name if chat.agent else None
        chat.agent_avatar = chat.agent.avatar if chat.agent else None
        
        return chat
        
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"数据完整性错误 - 创建聊天: {str(e)}")
        if "user_id" in str(e):
            raise HTTPException(status_code=400, detail="无效的用户ID")
        elif "agent_id" in str(e):
            raise HTTPException(status_code=400, detail="无效的Agent ID")
        else:
            raise HTTPException(status_code=400, detail="数据完整性约束违反")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 创建聊天: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 创建聊天: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

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
    根据用户ID和Agent ID获取或创建唯一的聊天会话
    每个用户和每个Agent只能有一个会话
    """
    try:
        logger.info(f"获取或创建聊天会话 - 用户ID: {user_id}, Agent ID: {agent_id}")
        
        # 首先查找是否已存在会话
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
            logger.info(f"找到已存在的聊天会话 - Chat ID: {existing_chat.id}, Agent ID: {existing_chat.agent_id}")
            
            # 验证agent_id的一致性
            if existing_chat.agent_id != agent_id:
                logger.error(f"聊天会话中的Agent ID不匹配！期望: {agent_id}, 实际: {existing_chat.agent_id}")
                raise HTTPException(status_code=500, detail=f"聊天会话数据不一致: 期望Agent ID {agent_id}, 实际 {existing_chat.agent_id}")
            
            # 获取最近消息和时间戳
            try:
                session_id = generate_session_id(existing_chat.id)
                last_message_data = chat_history_service.get_last_message_with_timestamp(session_id)
                
                if last_message_data:
                    existing_chat.last_message = last_message_data['content']
                    existing_chat.last_message_time = last_message_data['timestamp']
                else:
                    existing_chat.last_message = None
                    existing_chat.last_message_time = None
            except Exception as e:
                logger.error(f"获取最近消息失败: {str(e)}")
                existing_chat.last_message = None
                existing_chat.last_message_time = None
            existing_chat.agent_name = existing_chat.agent.name if existing_chat.agent else None
            existing_chat.agent_avatar = existing_chat.agent.avatar if existing_chat.agent else None
            return existing_chat
        
        # 如果不存在，则创建新的会话
        logger.info(f"未找到已存在的聊天会话，创建新的会话 - Agent ID: {agent_id}")
        
        # 首先验证Agent是否存在
        agent_result = await db.execute(
            select(models.Agent)
            .where(models.Agent.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            logger.error(f"Agent不存在: {agent_id}")
            raise HTTPException(status_code=404, detail="Agent不存在")
        
        logger.info(f"验证Agent存在 - Agent ID: {agent.id}, Name: {agent.name}")
        
        # 创建新的聊天会话
        chat_id = str(uuid.uuid4())
        db_chat = models.Chat(
            id=chat_id,
            user_id=user_id,
            agent_id=agent_id  # 确保使用传入的agent_id
        )
        
        logger.info(f"创建新聊天会话 - Chat ID: {chat_id}, User ID: {user_id}, Agent ID: {agent_id}")
        
        db.add(db_chat)
        await db.commit()
        await db.refresh(db_chat)
        
        # 验证创建后的agent_id
        if db_chat.agent_id != agent_id:
            logger.error(f"创建聊天会话后Agent ID不匹配！期望: {agent_id}, 实际: {db_chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"创建聊天会话失败: Agent ID不匹配")
        
        # 添加Agent开场白到chat_history
        if agent.opening:
            try:
                session_id = generate_session_id(chat_id)
                chat_history_service.add_agent_opening_message(session_id, agent.opening)
                logger.info(f"添加Agent开场白成功 - Session ID: {session_id}")
            except Exception as e:
                logger.error(f"添加开场白失败: {str(e)}")
                # 继续执行，不影响chat创建
        
        # 重新查询以加载关系数据
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings),
                selectinload(models.Chat.agent)
            )
            .where(models.Chat.id == db_chat.id)
        )
        new_chat = result.scalar_one()
        
        # 最终验证
        if new_chat.agent_id != agent_id:
            logger.error(f"重新查询后Agent ID不匹配！期望: {agent_id}, 实际: {new_chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"聊天会话数据异常: Agent ID不匹配")
        
        # 获取最近消息和时间戳以及agent名称
        try:
            session_id = generate_session_id(new_chat.id)
            last_message_data = chat_history_service.get_last_message_with_timestamp(session_id)
            
            if last_message_data:
                new_chat.last_message = last_message_data['content']
                new_chat.last_message_time = last_message_data['timestamp']
            else:
                new_chat.last_message = None
                new_chat.last_message_time = None
        except Exception as e:
            logger.error(f"获取最近消息失败: {str(e)}")
            new_chat.last_message = None
            new_chat.last_message_time = None
        new_chat.agent_name = new_chat.agent.name if new_chat.agent else None
        new_chat.agent_avatar = new_chat.agent.avatar if new_chat.agent else None
        
        logger.info(f"成功创建新聊天会话 - Chat ID: {new_chat.id}, Agent ID: {new_chat.agent_id}")
        return new_chat
        
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
            voice_enabled=True,
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