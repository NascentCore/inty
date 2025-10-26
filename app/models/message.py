import enum

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models import Base


class MessageType(str, enum.Enum):
    """消息类型"""

    TEXT = "TEXT"
    VOICE = "VOICE"
    IMAGE = "IMAGE"


class SenderType(str, enum.Enum):
    """发送者类型"""

    USER = "USER"
    AI = "AI"


# DEPRECATED: 这个表从来没有被使用过
class Message(Base):
    """消息模型"""

    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    content = Column(String)
    type = Column(Enum(MessageType), default=MessageType.TEXT)
    sender_type = Column(Enum(SenderType))
    created_at = Column(DateTime(timezone=True), server_default=sa.text("now()"))

    # 外键
    sender_id = Column(String, ForeignKey("users.id"))
    agent_id = Column(String, ForeignKey("agents.id"))

    # 关系
    sender = relationship("User", back_populates="messages")
    agent = relationship("Agent", back_populates="messages")

    # 聊天关联
    chat_id = Column(String, ForeignKey("chats.id"))
    chat = relationship("Chat")
