from sqlalchemy import Boolean, Column, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import sqlalchemy as sa

from app.db.base_class import Base
from app.models.associations import agent_followers
from app.models.notification import UserNotification


class AuthType(str, enum.Enum):
    """认证类型"""
    PHONE = "PHONE"
    GOOGLE = "GOOGLE"
    GUEST = "GUEST"


class Gender(str, enum.Enum):
    """性别"""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, comment="用户唯一标识符")
    nickname = Column(String, index=True, comment="用户昵称，可搜索")
    avatar = Column(String, comment="用户头像URL")
    email = Column(String, unique=True, comment="邮箱地址，唯一，用于登录")
    phone = Column(String, unique=True, comment="手机号码，唯一，用于登录")
    gender = Column(Enum(Gender), comment="性别：男/女/其他")
    age_group = Column(String, comment="年龄段")
    description = Column(String, comment="个人简介")
    auth_type = Column(Enum(AuthType), nullable=False, comment="认证类型：手机号/Google/游客")
    google_id = Column(String, unique=True, comment="Google账号ID，唯一，用于Google登录")
    device_id = Column(String, unique=True, comment="设备ID，唯一，用于设备识别")
    system_language = Column(String, default="en", comment="系统语言偏好，默认英语")
    is_active = Column(Boolean, default=True, comment="账号是否激活")
    is_superuser = Column(Boolean, default=False, comment="是否为超级管理员")
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'), comment="更新时间")

    # 关系
    agents = relationship("Agent", back_populates="creator")
    following_agents = relationship(
        "Agent",
        secondary=agent_followers,
        back_populates="followers"
    )
    messages = relationship("Message", back_populates="sender")
    chat_settings = relationship("ChatSettings", back_populates="user")
    chats = relationship("Chat", back_populates="user")
    resources = relationship("Resource", back_populates="user")
    settings = relationship("Settings", back_populates="user", uselist=False)
    reports = relationship("Report", back_populates="reporter")
    notifications = relationship("UserNotification", back_populates="user")