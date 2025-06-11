from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, UniqueConstraint, Index
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
    
    # 唯一约束：每个用户与每个Agent只能有一个活跃的聊天会话
    # 注意：这里先添加普通索引，实际的唯一约束将通过迁移文件添加
    __table_args__ = (
        Index('ix_chats_user_agent_active', 'user_id', 'agent_id', 'is_active'),
    )
    
    # 非数据库字段，用于存储最近消息和agent名称
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_message = None
        self._last_message_time = None
        self._agent_name = None
        self._agent_avatar = None
    
    @property 
    def last_message(self):
        return getattr(self, '_last_message', None)
    
    @last_message.setter
    def last_message(self, value):
        self._last_message = value
        
    @property 
    def last_message_time(self):
        return getattr(self, '_last_message_time', None)
    
    @last_message_time.setter
    def last_message_time(self, value):
        self._last_message_time = value
        
    @property 
    def agent_name(self):
        return getattr(self, '_agent_name', None)
    
    @agent_name.setter
    def agent_name(self, value):
        self._agent_name = value

    @property 
    def agent_avatar(self):
        return getattr(self, '_agent_avatar', None)
    
    @agent_avatar.setter
    def agent_avatar(self, value):
        self._agent_avatar = value