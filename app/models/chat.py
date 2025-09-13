from typing import List
import warnings
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


from app.models import Base


class Chat(Base):
    """
    存储用户和Agent的聊天会话的设定信息，具体聊天消息存储于 chat_history 表
    可以保存 user & agent ID，用户进行聊天时，查询 user agent 信息，构建 system messages
    进行聊天。

    也可以保存 system messages，聊天时，直接将 system messages & chat messages。
    """
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True, comment="Chat name")
    user_id = Column(
        String, ForeignKey("users.id"), nullable=False, comment="The ID of the user"
    )
    agent_id = Column(
        String,
        ForeignKey("agents.id"),
        nullable=False,
        comment="The ID of the agent chatting with the user",
    )

    # Why need this? Should deleted_at is not None enough?
    is_active = Column(Boolean, default=True)

    system_messages = Column(
        ARRAY(String), comment="System messages to be used for the chat"
    )

    # 调试功能字段（通过全局配置控制是否启用）
    # DEPRECATED: This field is not needed anymore.
    debug_messages = Column(
        JSON,
        nullable=True,
        comment="最新一次发送给大模型的完整messages列表（JSON格式）",
    )

    # 关系
    user = relationship("User", back_populates="chats")
    agent = relationship("Agent", back_populates="chats")
    settings = relationship("ChatSettings", back_populates="chat", uselist=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    # 唯一约束：每个用户与每个Agent只能有一个活跃的聊天会话
    # 注意：这里先添加普通索引，实际的唯一约束将通过迁移文件添加
    __table_args__ = (
        Index("ix_chats_user_agent_active", "user_id", "agent_id", "is_active"),
        Index(
            "uq_chats_user_agent_active",
            "user_id",
            "agent_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
    )

    # 非数据库字段，用于存储最近消息和agent名称
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_message = None
        self._last_message_time = None
        self._agent_name = None
        self._agent_avatar = None
        self._agent_is_deleted = None

    @property
    def debug_messages(self):
        warnings.warn(
            "debug_messages is deprecated and will be removed in the future. Use system_messages instead.",
            DeprecationWarning,
        )
        return self._debug_messages

    @debug_messages.setter
    def debug_messages(self, value):
        warnings.warn(
            "debug_messages is deprecated and will be removed in the future. Use system_messages instead.",
            DeprecationWarning,
        )
        self._debug_messages = value

    @property
    def last_message(self):
        return getattr(self, "_last_message", None)

    @last_message.setter
    def last_message(self, value):
        self._last_message = value

    @property
    def last_message_time(self):
        return getattr(self, "_last_message_time", None)

    @last_message_time.setter
    def last_message_time(self, value):
        self._last_message_time = value

    @property
    def agent_name(self):
        return getattr(self, "_agent_name", None)

    @agent_name.setter
    def agent_name(self, value):
        self._agent_name = value

    @property
    def agent_avatar(self):
        return getattr(self, "_agent_avatar", None)

    @agent_avatar.setter
    def agent_avatar(self, value):
        self._agent_avatar = value

    @property
    def agent_is_deleted(self):
        return getattr(self, "_agent_is_deleted", None)

    @agent_is_deleted.setter
    def agent_is_deleted(self, value):
        self._agent_is_deleted = value
