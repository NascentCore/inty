from sqlalchemy import UUID, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.models.base import Base

TABLE_NAME = "chat_history"


class ChatHistory(Base):
    __tablename__ = TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    message = Column(JSONB, nullable=False)
    audio_url = Column(String, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="软删除时间")
