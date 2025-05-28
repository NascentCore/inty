from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid

from app.models.user import User, AuthType, Gender
from app.schemas.auth import UserCreate, UserInfo
from app.core.security import get_password_hash


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """通过ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """通过邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    """通过手机号获取用户"""
    return db.query(User).filter(User.phone == phone).first()


def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    """通过Google ID获取用户"""
    return db.query(User).filter(User.google_id == google_id).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    """创建用户"""
    user_id = str(uuid.uuid4())
    
    # 创建用户对象
    user = User(
        id=user_id,
        auth_type=user_in.auth_type,
        system_language=user_in.user_info.system_language if user_in.user_info else "en"
    )
    
    # 根据认证类型设置用户信息
    if user_in.auth_type == AuthType.PHONE:
        user.phone = user_in.auth_data.phone
    elif user_in.auth_type == AuthType.GOOGLE:
        user.google_id = user_in.auth_data.google_id
    
    # 设置用户信息
    if user_in.user_info:
        user.gender = user_in.user_info.gender
        user.age_group = user_in.user_info.age_group
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def update_user(
    db: Session,
    *,
    user: User,
    user_info: Optional[UserInfo] = None,
    **kwargs
) -> User:
    """更新用户信息"""
    if user_info:
        if user_info.gender:
            user.gender = user_info.gender
        if user_info.age_group:
            user.age_group = user_info.age_group
        if user_info.system_language:
            user.system_language = user_info.system_language
    
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def get_user_dict(user: User) -> Dict[str, Any]:
    """获取用户字典"""
    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "email": user.email,
        "phone": user.phone,
        "gender": user.gender,
        "age_group": user.age_group,
        "description": user.description,
        "auth_type": user.auth_type,
        "system_language": user.system_language,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    } 