from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
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
    settings = relationship("ChatSettings", back_populates="chat", uselist=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'))
    
    # 非数据库字段，用于存储最近消息和agent名称
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_message = None
        self._agent_name = None
    
    @property 
    def last_message(self):
        return getattr(self, '_last_message', None)
    
    @last_message.setter
    def last_message(self, value):
        self._last_message = value
        
    @property 
    def agent_name(self):
        return getattr(self, '_agent_name', None)
    
    @agent_name.setter
    def agent_name(self, value):
        self._agent_name = value