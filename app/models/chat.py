from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import sqlalchemy as sa

from app.db.base_class import Base


class Chat(Base):
    """聊天模型"""
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # 关系
    user = relationship("User", back_populates="chats")
    agent = relationship("Agent", back_populates="chats")
    messages = relationship("Message", back_populates="chat")
    settings = relationship("ChatSettings", back_populates="chat", uselist=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()')) 