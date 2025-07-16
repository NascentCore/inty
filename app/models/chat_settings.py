from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import sqlalchemy as sa

from app.db.base_class import Base


class ChatSettings(Base):
    """聊天设置模型"""
    __tablename__ = "chat_settings"

    id = Column(String, primary_key=True, index=True)
    language = Column(String, default="en")
    voice_enabled = Column(Boolean, default=True)  # 个性化语音自动播放开关
    keep_talking = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'))

    # 外键
    user_id = Column(String, ForeignKey("users.id"))
    agent_id = Column(String, ForeignKey("agents.id"))

    # 关系
    user = relationship("User", back_populates="chat_settings")
    agent = relationship("Agent", back_populates="chat_settings")

    chat_id = Column(String, ForeignKey("chats.id"))
    chat = relationship("Chat", back_populates="settings") 