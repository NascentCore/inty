import sqlalchemy as sa
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class FeedbackPushHistory(Base):
    """Feedback 推送历史记录模型"""

    __tablename__ = "feedback_push_history"

    id = Column(String, primary_key=True, index=True, comment="推送记录ID")
    user_id = Column(
        String, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID"
    )
    chat_count_threshold = Column(
        Integer,
        nullable=False,
        comment="触发的聊天轮数阈值（20/30/40/50/60）",
    )
    sent_at = Column(DateTime(timezone=True), nullable=False, comment="发送时间")
    created_at = Column(DateTime(timezone=True), server_default=sa.text("now()"))

    # 关系
    user = relationship("User")

    # 索引和约束
    __table_args__ = (
        Index("ix_feedback_push_user_id", "user_id"),
        Index("ix_feedback_push_sent_at", "sent_at"),
        Index("ix_feedback_push_chat_count_threshold", "chat_count_threshold"),
        # 唯一约束：确保每个用户每个阈值只触发一次
        UniqueConstraint(
            "user_id",
            "chat_count_threshold",
            name="uq_feedback_push_user_threshold",
        ),
    )
