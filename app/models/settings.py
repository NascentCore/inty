import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Settings(Base):
    """用户设置模型"""

    __tablename__ = "settings"

    id = Column(String, primary_key=True, index=True)
    language = Column(String, default="en")  # 系统语言
    voice_enabled = Column(Boolean, default=True)  # 是否启用语音
    keep_talking = Column(
        Boolean, default=True
    )  # DEPRECATED: 该功能已弃用，保留字段仅为向后兼容

    # 关系
    user = relationship("User", back_populates="settings")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    # 外键
    user_id = Column(String, ForeignKey("users.id"), unique=True)
