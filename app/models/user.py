import enum
from datetime import UTC, datetime

import sqlalchemy as sa
from loguru import logger
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship, validates

from app.models.base import Base


class AuthType(str, enum.Enum):
    """认证类型"""

    # 目前未使用
    PHONE = "PHONE"
    GOOGLE = "GOOGLE"
    GUEST = "GUEST"
    # 使用 Email+Password 登录
    # （2025-11-27）目前仅用于让 Google Play 审查员登录
    EMAIL = "EMAIL"


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
        String(8),
        comment="DEPRECATED: use User.id; legacy 8-digit display id",
        info={"deprecated": True},
    )
    # TODO: Use SERIAL instead of string.
    nickname = Column(String, index=True, comment="用户昵称，可搜索")
    avatar = Column(String, comment="用户头像URL")
    email = Column(String, comment="邮箱地址")
    user_photo = Column(String, comment="用户自拍照片URL，用于生图参考")
    selfie_persona_summary = Column(
        String(1024),
        comment="根据用户自拍推测的简短画像结论，用于聊天提示词",
    )

    @validates("phone")
    def validate_phone(self, key, value):
        if value:
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
    password = Column(
        String, nullable=True, comment="密码哈希，用于 email 登录"
    )
    device_id = Column(
        String, unique=True, comment="设备ID，唯一，用于设备识别"
    )
    system_language = Column(
        String, default="en", comment="系统语言偏好，默认英语"
    )
    meta_data = Column(
        JSON, nullable=True, comment="用户元数据（可扩展，例如 MBTI 类型）"
    )
    is_superuser = Column(Boolean, default=False, comment="是否为超级管理员")
    created_at = Column(
        DateTime(timezone=True),
        server_default=sa.text("now()"),
        comment="创建时间",
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=sa.text("now()"), comment="更新时间"
    )

    # 账户删除相关字段
    deleted_at = Column(DateTime(timezone=True), comment="账户删除时间")
    # DEPRECATED: This field is not needed anymore.
    anonymized_at = Column(DateTime(timezone=True), comment="数据匿名化时间")
    deletion_reason = Column(String(255), comment="删除原因")

    @property
    def is_active(self) -> bool:
        """Derived活跃状态，仅当 deleted_at 为空时视为活跃。"""
        return self.deleted_at is None

    # FCM token 相关字段
    fcm_token_invalid_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="FCM token 无效时间，如果为 None 表示用户有有效 token 或未检查，如果有值表示在这个时间点发现用户所有 token 都无效",
    )

    # 用于 push worker 的 feature gating：worker 根据此值决定是否发送或如何构造 push
    last_android_app_version_code = Column(
        Integer,
        nullable=True,
        comment="Last Android app version code reported by client on POST /api/v1/version/check; used for feature gating in the push worker. Android-specific because backend may serve iOS in the future.",
    )

    # 关系
    agents = relationship("Agent", back_populates="creator")
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
    subscription_usage = relationship(
        "SubscriptionUsage", back_populates="user"
    )

    # 评测相关关系
    evaluation_sessions = relationship(
        "EvaluationSession", back_populates="creator"
    )


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True)
    token = Column(Text, nullable=False, unique=True)
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
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
