from sqlalchemy import Boolean, Column, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import sqlalchemy as sa

from app.db.base_class import Base
from app.models.associations import agent_followers


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

    id = Column(String, primary_key=True, index=True)
    nickname = Column(String, index=True)
    avatar = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String, unique=True, index=True)
    gender = Column(Enum(Gender))
    age_group = Column(String)
    description = Column(String)
    auth_type = Column(Enum(AuthType), nullable=False)
    google_id = Column(String, unique=True, index=True)
    device_id = Column(String, unique=True, index=True)
    system_language = Column(String, default="en")
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'))

    # 关系
    agents = relationship("Agent", back_populates="creator")
    following_agents = relationship(
        "Agent",
        secondary=agent_followers,
        back_populates="followers"
    )
    messages = relationship("Message", back_populates="sender")
    chat_settings = relationship("ChatSettings", back_populates="user")
    chats = relationship("Chat", back_populates="user")
    resources = relationship("Resource", back_populates="user")
    settings = relationship("Settings", back_populates="user", uselist=False) 