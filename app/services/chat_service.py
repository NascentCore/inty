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
            # 获取最近消息 (chat_id 等于 session_id)
            try:
                chat.last_message = chat_history_service.get_last_message(chat.id)
            except Exception as e:
                logger.error(f"获取最近消息失败: {str(e)}")
                chat.last_message = None
            # 设置agent名称
            chat.agent_name = chat.agent.name if chat.agent else None
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
    获取用户的聊天列表
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
            .offset(skip)
            .limit(limit)
            .order_by(models.Chat.updated_at.desc())
        )
        chats = result.scalars().all()
        
        # 为每个chat获取最近消息和agent名称
        for chat in chats:
            try:
                chat.last_message = chat_history_service.get_last_message(chat.id)
            except Exception as e:
                logger.error(f"获取最近消息失败: {str(e)}")
                chat.last_message = None
            chat.agent_name = chat.agent.name if chat.agent else None
            
        return chats
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
        # 生成唯一ID (这个ID同时作为session_id)
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
        
        # 添加Agent开场白到chat_history (chat_id 作为 session_id)
        if agent.opening:
            try:
                chat_history_service.add_agent_opening_message(chat_id, agent.opening)
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
        
        # 获取最近消息 (应该是刚添加的开场白) 和agent名称
        try:
            chat.last_message = chat_history_service.get_last_message(chat.id)
        except Exception as e:
            logger.error(f"获取最近消息失败: {str(e)}")
            chat.last_message = None
        chat.agent_name = chat.agent.name if chat.agent else None
        
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