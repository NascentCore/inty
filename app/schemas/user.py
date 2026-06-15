from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator

from app.models.user import AuthType, Gender


class ActionType(str, Enum):
    """用户行动类型枚举"""

    REQUEST_FEEDBACK = "request_feedback"


MBTI_TYPES = {
    "INTJ",
    "INTP",
    "ENTJ",
    "ENTP",
    "INFJ",
    "INFP",
    "ENFJ",
    "ENFP",
    "ISTJ",
    "ISFJ",
    "ESTJ",
    "ESFJ",
    "ISTP",
    "ISFP",
    "ESTP",
    "ESFP",
}


class UserMetadata(BaseModel):
    """用户元数据（用于 users.meta_data 列）。"""

    mbti_type: Optional[str] = None

    @validator("mbti_type")
    def validate_mbti_type(cls, v):
        if v is None or v == "":
            return None
        normalized = v.strip().upper()
        if normalized not in MBTI_TYPES:
            raise ValueError(f"Unsupported MBTI type: {v}")
        return normalized


class UserBase(BaseModel):
    """用户基础信息"""

    # DEPRECATED: app 显示 ID 而非 readable_id
    readable_id: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[str] = None  # 改为普通str，避免EmailStr验证问题
    user_photo: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    age_group: Optional[str] = None
    description: Optional[str] = None
    system_language: Optional[str] = None

    @validator("email")
    def validate_email(cls, v):
        """宽松的邮箱验证，允许特殊域名如.local"""
        if v is None or v == "":
            return v
        # 如果包含@且格式基本正确就通过，不做严格验证
        if "@" in v and "." in v.split("@")[1]:
            return v
        # 对于特殊的已删除用户邮箱，直接通过
        if "deleted_user_" in v and "@anonymized.local" in v:
            return v
        return v


class UserCreate(UserBase):
    """创建用户"""

    auth_type: str
    user_info: Optional[dict] = None
    request_id: Optional[str] = None


class UserUpdate(BaseModel):
    """更新用户信息"""

    nickname: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[str] = None  # 改为普通str
    user_photo: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    age_group: Optional[str] = None
    description: Optional[str] = None
    system_language: Optional[str] = None
    request_id: Optional[str] = None

    @validator("nickname")
    def validate_nickname(cls, v):
        if v is None:
            return v
        return v.strip()

    @validator("email")
    def validate_email(cls, v):
        """宽松的邮箱验证"""
        if v is None or v == "":
            return v
        if "@" in v and "." in v.split("@")[1]:
            return v
        if "deleted_user_" in v and "@anonymized.local" in v:
            return v
        return v


class UserInDBBase(UserBase):
    """数据库中的用户信息"""

    id: str
    # DEPRECATED: app 显示 ID 而非 readable_id
    readable_id: Optional[str] = None
    auth_type: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_superuser: bool = False

    class Config:
        from_attributes = True


class UserAction(BaseModel):
    """用户行动项"""

    type: ActionType
    enabled: bool


class User(UserInDBBase):
    """返回给客户端的用户信息"""

    public_agents_count: Optional[int] = 0
    total_public_agents_follows: Optional[int] = 0
    followers_count: Optional[int] = 0
    connector_count: Optional[int] = 0
    actions: list[UserAction] = Field(default_factory=list)


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
    request_id: Optional[str] = None


class UserListItem(BaseModel):
    """用户列表项"""

    id: str
    readable_id: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[str] = None
    user_photo: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    age_group: Optional[str] = None
    description: Optional[str] = None
    auth_type: AuthType
    google_id: Optional[str] = None
    device_id: Optional[str] = None
    system_language: Optional[str] = None
    connector_count: Optional[int] = 0
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    anonymized_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None

    class Config:
        from_attributes = True


class UserList(BaseModel):
    """用户列表响应"""

    total: int
    skip: int
    limit: int
    items: list[UserListItem]
    has_more: bool
