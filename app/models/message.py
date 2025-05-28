from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import sqlalchemy as sa

from app.db.base_class import Base


class MessageType(str, enum.Enum):
    """消息类型"""
    TEXT = "TEXT"
    VOICE = "VOICE"
    IMAGE = "IMAGE"


class SenderType(str, enum.Enum):
    """发送者类型"""
    USER = "USER"
    AI = "AI"


class Message(Base):
    """消息模型"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    content = Column(String)
    type = Column(Enum(MessageType), default=MessageType.TEXT)
    sender_type = Column(Enum(SenderType))
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'))

    # 外键
    sender_id = Column(String, ForeignKey("users.id"))
    agent_id = Column(String, ForeignKey("agents.id"))

    # 关系
    sender = relationship("User", back_populates="messages")
    agent = relationship("Agent", back_populates="messages")

    chat_id = Column(String, ForeignKey("chats.id"))
    chat = relationship("Chat", back_populates="messages") 