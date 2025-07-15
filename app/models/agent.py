from sqlalchemy import Boolean, Column, String, DateTime, Enum, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import sqlalchemy as sa

from app.db.base_class import Base
from app.models.associations import agent_followers
from app.models.user import Gender


class AgentStatus(str, enum.Enum):
    """AI角色状态"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AgentVisibility(str, enum.Enum):
    """AI角色可见性"""
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class Agent(Base):
    """AI角色模型"""
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    readable_id = Column(String(8), unique=True, index=True, nullable=False)
    name = Column(String(30), index=True, nullable=False)
    gender = Column(Enum(Gender, name="gender"), nullable=False)
    avatar = Column(String)
    background = Column(String)
    background_images = Column(JSON)  # 存储背景图列表
    voice_id = Column(String)
    settings = Column(JSON)
    intro = Column(String)
    opening = Column(String)
    visibility = Column(Enum(AgentVisibility, name="visibility"), default=AgentVisibility.PUBLIC)
    photos = Column(JSON)
    category = Column(String)
    status = Column(Enum(AgentStatus, name="agentstatus"), default=AgentStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    prompt = Column(String)

    # 角色卡相关字段
    character_card_spec = Column(String, nullable=True)  # 角色卡规范版本
    character_card_data = Column(JSON, nullable=True)  # 原始角色卡数据
    personality = Column(Text, nullable=True)  # 性格特征
    scenario = Column(Text, nullable=True)  # 场景设定
    first_message = Column(Text, nullable=True)  # 第一条消息
    message_example = Column(Text, nullable=True)  # 对话示例
    creator_notes = Column(Text, nullable=True)  # 创建者备注
    post_history_instructions = Column(Text, nullable=True)  # 历史后指令
    alternate_greetings = Column(JSON, nullable=True)  # 替代问候语
    character_book = Column(JSON, nullable=True)  # 角色书
    tags = Column(JSON, nullable=True)  # 标签
    character_version = Column(String, nullable=True)  # 版本号
    extensions = Column(JSON, nullable=True)  # 扩展数据

    # 外键
    creator_id = Column(String, ForeignKey("users.id"))

    # 关系
    creator = relationship("User", back_populates="agents")
    followers = relationship(
        "User",
        secondary=agent_followers,
        back_populates="following_agents"
    )
    messages = relationship("Message", back_populates="agent")
    chat_settings = relationship("ChatSettings", back_populates="agent")
    chats = relationship("Chat", back_populates="agent")
    resources = relationship("Resource", back_populates="agent") 