"""角色主题专区模型"""

from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class CharacterThemeVisibility(StrEnum):
    """角色主题专区可见性"""

    PRIMARY = "PRIMARY"  # 第一展示
    SECONDARY = "SECONDARY"  # 第二展示
    HIDDEN = "HIDDEN"  # 不可见


class CharacterTheme(Base):
    """角色主题专区模型"""

    __tablename__ = "character_themes"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="专区名称")
    description = Column(Text, nullable=True, comment="专区描述")
    background_image_url = Column(String, nullable=True, comment="背景图URL地址")
    visibility = Column(
        Enum(CharacterThemeVisibility, name="character_theme_visibility"),
        default=CharacterThemeVisibility.HIDDEN,
        nullable=False,
        index=True,
        comment="可见性：第一展示、第二展示、不可见",
    )
    created_at = Column(DateTime(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    # 关系
    agents = relationship(
        "CharacterThemeAgent",
        back_populates="theme",
        cascade="all, delete-orphan",
        order_by="CharacterThemeAgent.order_index",
    )


class CharacterThemeAgent(Base):
    """角色主题专区与角色的关联表"""

    __tablename__ = "character_theme_agents"

    theme_id = Column(
        String, ForeignKey("character_themes.id", ondelete="CASCADE"), primary_key=True
    )
    agent_id = Column(
        String, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    order_index = Column(
        Integer, nullable=False, comment="角色在专区中的顺序（从0开始）"
    )

    # 关系
    theme = relationship("CharacterTheme", back_populates="agents")
    agent = relationship("Agent")
