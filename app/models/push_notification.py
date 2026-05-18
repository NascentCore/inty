import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class PushNotificationHistory(Base):
    """推送通知历史记录模型"""

    __tablename__ = "push_notification_history"

    id = Column(String, primary_key=True, index=True)
    chat_id = Column(
        String,
        ForeignKey("chats.id"),
        nullable=True,
        index=True,
        comment="聊天ID（可选，无聊天推送时为空）",
    )
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(
        String, ForeignKey("agents.id"), nullable=False, index=True
    )
    push_type = Column(
        String,
        nullable=False,
        comment="推送类型: no_chat（无聊天推送）, recent_chat（最近聊天推送）",
    )
    stage = Column(
        String,
        nullable=False,
        comment="推送阶段: 10min, 30min, 2h, 24h, 48h",
    )
    message_content = Column(Text, nullable=True, comment="生成的Agent消息内容")
    sent_at = Column(
        DateTime(timezone=True), nullable=False, comment="发送时间"
    )
    read_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="已读时间（用户发送新消息时标记为已读）",
    )
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )

    # 关系
    chat = relationship("Chat")
    user = relationship("User")
    agent = relationship("Agent")

    # 索引（已移除唯一约束，使用 read_at 字段标记已读状态）
    __table_args__ = (
        Index("ix_push_notification_user_id", "user_id"),
        Index("ix_push_notification_agent_id", "agent_id"),
        Index("ix_push_notification_sent_at", "sent_at"),
        Index("ix_push_notification_push_type", "push_type"),
        Index("ix_push_notification_read_at", "read_at"),
        # 复合索引：用于查询未读推送
        Index(
            "ix_push_notification_chat_stage_unread",
            "chat_id",
            "stage",
            "read_at",
            postgresql_where=sa.text("read_at IS NULL AND chat_id IS NOT NULL"),
        ),
        Index(
            "ix_push_notification_user_stage_unread",
            "user_id",
            "stage",
            "read_at",
            postgresql_where=sa.text("read_at IS NULL AND chat_id IS NULL"),
        ),
    )
