from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging
import traceback
import uuid

from app.core.uuid import uid
from app.models import User
from app.models.user import AuthType
from app.schemas import UserUpdate

logger = logging.getLogger(__name__)

def register_user(db: Session, user_in) -> User:
    """注册用户（手机号等）"""
    try:
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            auth_type=user_in.auth_type,
            system_language=user_in.user_info.system_language if user_in.user_info else "en",
            is_active=True
        )
        if user_in.user_info:
            user.gender = user_in.user_info.gender
            user.age_group = user_in.user_info.age_group
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        logger.error(f"注册用户失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise e

def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    """通过手机号获取用户"""
    return db.query(User).filter(User.phone == phone).first()

async def create_guest_user(
    db: AsyncSession,
    device_id: Optional[str] = None,
    system_language: Optional[str] = None
) -> User:
    """创建游客用户"""
    try:
        if device_id:
            stmt = select(User).where(
                User.device_id == device_id,
                User.auth_type == AuthType.GUEST
            )
            result = await db.execute(stmt)
            existing_user = result.scalars().first()
            if existing_user:
                return existing_user
        user_id = uid(prefix="user")
        user = User(
            id=user_id,
            auth_type=AuthType.GUEST,
            device_id=device_id,
            nickname=f"Guest_{user_id[-8:]}",
            system_language=system_language or "en",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except Exception as e:
        logger.error(f"创建游客用户失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise e 

async def update_user(
    db: AsyncSession,
    user_id: str,
    user_in: UserUpdate
) -> User:
    """更新用户信息"""
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
            
        update_data = user_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
            
        await db.commit()
        await db.refresh(user)
        return user
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise e 

