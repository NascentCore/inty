import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class ChatSettings(Base):
    """聊天设置模型。

    注意：当前不包含「选择模型」字段。若产品在 chat settings 中提供模型选项，
    后端尚未落库与参与 chat completion；实际模型选择见 app.core.agent（角色配置）
    与 app.core.model_selection（订阅层）。
    """

    __tablename__ = "chat_settings"
    __table_args__ = (
        Index("uq_chat_settings_chat_id", "chat_id", unique=True),
    )

    id = Column(String, primary_key=True, index=True)
    language = Column(String, default="en")
    voice_enabled = Column(Boolean, default=True)  # 个性化语音自动播放开关
    voice_id = Column(
        String,
        nullable=True,
        comment="Per-chat selected voice id (MVP supports Gemini voices only)",
    )
    keep_talking = Column(Boolean, default=True)
    style_prompt = Column(
        Text, nullable=True, comment="风格提示词，仅订阅用户可设置"
    )
    # 对应的，App chat settings 中使用的名字是 premium model (vs mode)
    # 实际 backend 这里的实现仅仅是提示词的变化。
    premium_mode = Column(
        Boolean, default=False, comment="高级模式开关，仅订阅用户可设置"
    )
    chat_mode = Column(
        String,
        nullable=True,
        comment="User-selected chat mode id (e.g. flirting_mode_20250902). Null = use agent default.",
    )
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    # 外键
    user_id = Column(String, ForeignKey("users.id"))
    agent_id = Column(String, ForeignKey("agents.id"))

    # 关系
    user = relationship("User", back_populates="chat_settings")
    agent = relationship("Agent", back_populates="chat_settings")

    chat_id = Column(String, ForeignKey("chats.id"))
    chat = relationship("Chat", back_populates="settings")
