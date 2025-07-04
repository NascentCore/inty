from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.models.user import Gender, AuthType

class UserBase(BaseModel):
    """用户基础信息"""
    readable_id: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    age_group: Optional[str] = None
    description: Optional[str] = None
    system_language: Optional[str] = None

class UserCreate(UserBase):
    """创建用户"""
    auth_type: str
    user_info: Optional[dict] = None

class UserUpdate(UserBase):
    """更新用户信息"""
    pass

class UserInDBBase(UserBase):
    """数据库中的用户信息"""
    id: str
    readable_id: str
    auth_type: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_superuser: bool = False

    class Config:
        from_attributes = True

class User(UserInDBBase):
    """返回给客户端的用户信息"""
    public_agents_count: Optional[int] = None
    total_public_agents_follows: Optional[int] = None

class UserInDB(UserInDBBase):
    """数据库中的完整用户信息"""
    pass

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None 

class AvatarUploadResponse(BaseModel):
    avatar: str

class DeviceTokenRegister(BaseModel):
    """设备token注册请求"""
    token: str