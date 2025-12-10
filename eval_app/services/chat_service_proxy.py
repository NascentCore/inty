# CREATED_BY_AGENT
"""
Chat 服务代理 - 直接调用主应用的服务层
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.services import chat_service


async def get_chats(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
) -> List[schemas.Chat]:
    """获取用户的聊天列表"""
    return await chat_service.get_chats(db, user_id=user_id, skip=skip, limit=limit)


async def create_chat(
    db: AsyncSession, chat_in: schemas.ChatCreate, user_id: str
) -> schemas.Chat:
    """创建聊天"""
    return await chat_service.create_chat(db, chat_in=chat_in, user_id=user_id)


async def delete_chat(db: AsyncSession, chat_id: str, user_id: str) -> schemas.Chat:
    """删除聊天"""
    return await chat_service.delete_chat(db, chat_id=chat_id, user_id=user_id)

