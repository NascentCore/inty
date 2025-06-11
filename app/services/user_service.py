from datetime import datetime, UTC
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging
import traceback
import uuid

from app.core.uuid import uid
from app.models import User
from app.models.user import AuthType, DeviceToken
from app.schemas import UserUpdate
from app.core.config import settings

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

def generate_avatar_path(user_id: str, filename: str) -> str:
    ext = filename.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
        raise ValueError(f"Unsupported file type: {ext}")
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"avatars/{user_id}/avatar-{timestamp}-{unique_id}.{ext}"

def get_path_from_gcs_url(url: str) -> str:
    if not url:
        return ""
    parts = url.split(".com/")
    if len(parts) < 2:
        return ""
    path = parts[1]
    # 去掉bucket名前缀
    bucket = settings.gcs.bucket
    if path.startswith(bucket + "/"):
        path = path[len(bucket) + 1 :]
    return path

async def register_device_token(
    db: AsyncSession,
    token: str,
    user_id: str
) -> DeviceToken:
    """
    注册或更新设备token
    """
    try:
        # 查找是否已存在该token
        stmt = select(DeviceToken).where(DeviceToken.token == token)
        result = await db.execute(stmt)
        device_token = result.scalars().first()
        
        if device_token:
            # 如果存在，更新user_id
            device_token.user_id = user_id
        else:
            # 如果不存在，创建新记录
            device_token = DeviceToken(
                token=token,
                user_id=user_id
            )
            db.add(device_token)
            
        await db.commit()
        await db.refresh(device_token)
        return device_token
        
    except Exception as e:
        raise e

async def get_users_device_tokens(
    db: AsyncSession,
    user_ids: list[str]
) -> list[str]:
    """获取多个用户的所有设备token
    
    Args:
        db: 数据库会话
        user_ids: 用户ID列表
        
    Returns:
        list[str]: 设备token列表，如果没有记录则返回空列表
    """
    try:
        stmt = select(DeviceToken.token).where(DeviceToken.user_id.in_(user_ids))
        result = await db.execute(stmt)
        tokens = result.scalars().all()
        return tokens
    except Exception as e:
        logger.error(f"获取用户设备token失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise e
