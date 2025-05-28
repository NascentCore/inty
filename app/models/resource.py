from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import sqlalchemy as sa

from app.db.base_class import Base


class ResourceType(str, enum.Enum):
    """资源类型"""
    IMAGE = "IMAGE"
    VOICE = "VOICE"
    VIDEO = "VIDEO"


class Resource(Base):
    """资源模型"""
    __tablename__ = "resources"

    id = Column(String, primary_key=True, index=True)
    type = Column(Enum(ResourceType))
    url = Column(String)
    resource_metadata = Column(JSON)  # 存储资源的元数据，如尺寸、格式等
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'))

    # 外键
    user_id = Column(String, ForeignKey("users.id"))
    agent_id = Column(String, ForeignKey("agents.id"))

    # 关系
    user = relationship("User", back_populates="resources")
    agent = relationship("Agent", back_populates="resources") 