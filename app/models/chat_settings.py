from enum import StrEnum
import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text, Index
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
    keep_talking = Column(Boolean, default=True)
    style_prompt = Column(Text, nullable=True, comment="风格提示词，仅订阅用户可设置")

    class SystemPromptingMode(StrEnum):
        """
        指生成系统提示词的方式，系统提示词指的是输入到大模型中最开始的一组提示词。
        具体来说根据角色设定、用户信息、对话设置，及其他相关信息来生成系统提示词。

        该生成提示词。
        """

        # 指使用角色指定的提示词（无论是否空白）不进行任何额外的处理。
        STATIC = "static"

        # 指填充缺失的提示词，但不做额外处理。
        FILL_MISSING = "fill_missing"

        # 指强制替换已有的提示词，如聊天风格提示词会替换为暧昧模式（Flirting）模式。
        OVERRIDE = "override"

    sys_pmt_mode = Column(Enum(SystemPromptingMode, name="sys_pmt_mode"), default=SystemPromptingMode.FILL_MISSING)

    # 对应的，App chat settings 中使用的名字是 premium model (vs mode)
    # 实际 backend 这里的实现仅仅是提示词的变化。
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

    # TODO: 增加 mode，enum (vanila, standard, premium)
    # TODO: 增加 features，list[str] (keep_talking, style_prompt, auto_play_voice)
