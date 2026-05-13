"""Surprise Snap：用户与角色对话达到指定轮数时插入的专属照消息及解锁记录。"""

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from app.models.base import Base


class SurpriseSnapProgress(Base):
    """同一 user+agent 下按 exclusive_photos 顺序发放的进度。"""

    __tablename__ = "surprise_snap_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    next_photo_index = Column(Integer, nullable=False, default=0)
    __table_args__ = (
        UniqueConstraint(
            "user_id", "agent_id", name="uq_surprise_snap_progress_user_agent"
        ),
    )


class SurpriseSnapUnlock(Base):
    """免费用户用 credit 解锁某条 surprise_snap 消息后的记录。"""

    __tablename__ = "surprise_snap_unlock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    message_id = Column(
        Integer,
        ForeignKey("chat_history.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "user_id", "message_id", name="uq_surprise_snap_unlock_user_message"
        ),
    )
