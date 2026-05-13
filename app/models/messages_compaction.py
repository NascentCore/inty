import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class MessagesCompaction(Base):
    """
    Stores compacted overflow chat history per user-agent pair.
    Primary key is "{user_id}:{agent_id}".
    """

    __tablename__ = "messages_compaction"

    key = Column(String(255), primary_key=True, comment="user_id:agent_id")
    user_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    compacted_payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    __table_args__ = (
        Index("ix_messages_compaction_user_agent", "user_id", "agent_id"),
    )
