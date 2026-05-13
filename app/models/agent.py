from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.user import Gender


class AgentStatus(StrEnum):
    """AI角色状态"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AgentVisibility(StrEnum):
    """AI 角色可见性"""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class AgentSource(StrEnum):
    """AI 角色来源"""

    USER_CREATED = "USER_CREATED"  # 用户创建
    AUTO_GENERATED = "AUTO_GENERATED"  # 自动生成（如 Dify 脚本）


class Agent(Base):
    """AI 角色，Agent 的提法是早期的用词，改动比较麻烦，就沿用了。"""

    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    # DEPRECATED: app 显示 ID 而非 readable_id
    readable_id = Column(String(8), comment="【已废弃】角色可读ID")
    name = Column(String(256), index=True, nullable=False)
    gender = Column(Enum(Gender, name="gender"), nullable=False)
    avatar = Column(String)
    background = Column(String)
    background_images = Column(JSON)  # 存储背景图列表
    background_animated = Column(String, nullable=True)  # 存储 webp 动图 URL
    voice_id = Column(String)
    # 这里包含了 llm_config 和 chat_settings 的配置；llm_config 用于覆盖系统为
    # 免费用户和付费用户设置的默认模型。
    settings = Column(JSON)
    intro = Column(String)
    status_line = Column(
        String,
        nullable=True,
        comment="Short mood/tagline for chat header (iMate status line)",
    )
    opening = Column(String)
    visibility = Column(
        Enum(AgentVisibility, name="visibility"), default=AgentVisibility.PUBLIC
    )
    photos = Column(JSON)
    exclusive_photos = Column(
        JSON,
        nullable=True,
        comment="运营上传的专属角色照：每项含 image_url, caption, credits_required",
    )
    category = Column(String)
    status = Column(Enum(AgentStatus, name="agentstatus"), default=AgentStatus.PENDING)
    source = Column(
        Enum(AgentSource, name="agentsource"),
        nullable=True,
        default=AgentSource.USER_CREATED,
        comment="角色来源：用户创建或自动生成",
    )
    created_at = Column(DateTime(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(
        Integer,
        nullable=False,
        default=1,
        server_default=sa.text("1"),
    )
    points = Column(
        Integer,
        default=0,
        server_default=sa.text("0"),
        comment="角色积分，用于角色热度排名（boosting feature）",
    )
    prompt = Column(String)

    # 主提示词和模式提示词字段
    # 如果使用预设提示词，存储 prompt ID（如 "roleplay_main"）
    # 如果自定义，存储完整文本
    main_prompt = Column(
        Text, nullable=True
    )  # 主提示词 - 作为第一个system message，可以是预设 ID 或自定义文本
    mode_prompt = Column(
        Text, nullable=True
    )  # 模式提示词 - 放在角色设定提示词后面，可以是预设 ID 或自定义文本

    # 角色设定相关字段
    personality = Column(Text, nullable=True)  # 性格特征
    scenario = Column(Text, nullable=True)  # 场景设定
    message_example = Column(Text, nullable=True)  # 对话示例
    creator_notes = Column(Text, nullable=True)  # 创建者备注
    post_history_instructions = Column(Text, nullable=True)  # 历史后指令
    alternate_greetings = Column(JSON, nullable=True)  # 替代问候语
    character_book = Column(JSON, nullable=True)  # 角色书
    tags = Column(JSON, nullable=True)  # 标签
    character_version = Column(String, nullable=True)  # 版本号
    extensions = Column(JSON, nullable=True)  # 扩展数据
    meta_data = Column(JSON, nullable=True)  # 灵活的元数据

    # 语音相关字段
    opening_audio_url = Column(String, nullable=True)  # 预生成的开场白语音URL

    # 外键
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 关系
    creator = relationship("User", back_populates="agents")
    chat_settings = relationship("ChatSettings", back_populates="agent")
    chats = relationship("Chat", back_populates="agent")
    resources = relationship("Resource", back_populates="agent")

    # 乐观锁配置：使用 version 字段防止并发更新冲突
    # 更新时会自动检查版本号，不匹配则抛出 StaleDataError，成功更新后自动递增 version
    __mapper_args__ = {
        "version_id_col": version,
    }
