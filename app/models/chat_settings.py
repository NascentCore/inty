import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models import Base


class ChatSettings(Base):
    """聊天设置模型"""

    __tablename__ = "chat_settings"
    __table_args__ = (Index("uq_chat_settings_chat_id", "chat_id", unique=True),)

    id = Column(String, primary_key=True, index=True)
    language = Column(String, default="en")
    voice_enabled = Column(Boolean, default=True)  # 个性化语音自动播放开关
    keep_talking = Column(Boolean, default=True)  # DEPRECATED: 该功能已弃用，保留字段仅为向后兼容
    style_prompt = Column(Text, nullable=True, comment="风格提示词，仅订阅用户可设置")
    # App 中使用的名字是 premium model，这里仅仅是提示词的变化。
    premium_mode = Column(
        Boolean, default=False, comment="高级模式开关，仅订阅用户可设置"
    )
    created_at = Column(DateTime(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    # 外键
    user_id = Column(String, ForeignKey("users.id"))
    agent_id = Column(String, ForeignKey("agents.id"))

    # 关系
    user = relationship("User", back_populates="chat_settings")
    agent = relationship("Agent", back_populates="chat_settings")

    chat_id = Column(String, ForeignKey("chats.id"))
    chat = relationship("Chat", back_populates="settings")
