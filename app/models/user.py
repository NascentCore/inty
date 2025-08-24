import enum
from datetime import UTC, datetime
from loguru import logger

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship, validates

from app.models import Base
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

    # TODO: This should be a UUID, but we use string to allow prepend
    # category prefixes like user-<uuid> for better readability.
    id = Column(String, primary_key=True, comment="用户唯一标识符")

    readable_id = Column(
        String(8), unique=True, index=True, nullable=False, comment="用户可读ID"
    )
    nickname = Column(String, index=True, comment="用户昵称，可搜索")
    avatar = Column(String, comment="用户头像URL")
    email = Column(String, comment="邮箱地址")

    @validates("phone")
    def validate_phone(self, key, value):
        logger.warning(
            "The 'phone' is added without a clear plan to be used. Please do not use it. Ask @yaxiong if you need phone.",
            DeprecationWarning,
        )
        return value

    phone = Column(String, unique=True, comment="手机号码，唯一，用于登录")
    gender = Column(Enum(Gender), comment="性别：男/女/其他")
    age_group = Column(String, comment="年龄段")
    description = Column(String, comment="个人简介")
    auth_type = Column(
        Enum(AuthType), nullable=False, comment="认证类型：手机号/Google/游客"
    )
    google_id = Column(String, comment="Google账号ID，用于支持用户注册登录")
    device_id = Column(String, unique=True, comment="设备ID，唯一，用于设备识别")
    system_language = Column(String, default="en", comment="系统语言偏好，默认英语")
    is_active = Column(Boolean, default=True, comment="账号是否激活")
    is_superuser = Column(Boolean, default=False, comment="是否为超级管理员")
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()"), comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=sa.text("now()"), comment="更新时间"
    )

    # 账户删除相关字段
    deleted_at = Column(DateTime(timezone=True), comment="账户删除时间")
    # DEPRECATED: This field is not needed anymore.
    anonymized_at = Column(DateTime(timezone=True), comment="数据匿名化时间")
    deletion_reason = Column(String(255), comment="删除原因")

    # 关系
    agents = relationship("Agent", back_populates="creator")
    following_agents = relationship(
        "Agent", secondary=agent_followers, back_populates="followers"
    )
    messages = relationship("Message", back_populates="sender")
    chat_settings = relationship("ChatSettings", back_populates="user")
    chats = relationship("Chat", back_populates="user")
    resources = relationship("Resource", back_populates="user")
    settings = relationship("Settings", back_populates="user", uselist=False)
    reports = relationship("Report", back_populates="reporter")
    notifications = relationship("UserNotification", back_populates="user")
    device_tokens = relationship("DeviceToken", back_populates="user")

    # 订阅相关关系
    subscriptions = relationship("UserSubscription", back_populates="user")
    subscription_transactions = relationship(
        "SubscriptionTransaction", back_populates="user"
    )
    subscription_usage = relationship("SubscriptionUsage", back_populates="user")

    # 评测相关关系
    evaluation_sessions = relationship("EvaluationSession", back_populates="creator")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True)
    token = Column(Text, nullable=False, unique=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # 索引
    __table_args__ = (
        Index("ix_device_tokens_user_id", "user_id"),
        Index("ix_device_tokens_token", "token", unique=True),
    )

    # 关联关系
    user = relationship("User", back_populates="device_tokens")

    def __repr__(self):
        return f"<DeviceToken(id={self.id}, user_id={self.user_id})>"
