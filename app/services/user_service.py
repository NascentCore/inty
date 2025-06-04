from typing import Optional
from sqlalchemy.orm import Session
import logging
import traceback
import uuid

from app.core.uuid import uid
from app.models import User
from app.models.user import AuthType

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

def create_guest_user(
    db: Session,
    device_id: Optional[str] = None,
    system_language: Optional[str] = None
) -> User:
    """创建游客用户"""
    try:
        if device_id:
            existing_user = db.query(User).filter(
                User.device_id == device_id,
                User.auth_type == AuthType.GUEST
            ).first()
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
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        logger.error(f"创建游客用户失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise e 