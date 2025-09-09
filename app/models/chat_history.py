from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base_class import Base

TABLE_NAME = "chat_history"


class ChatHistory(Base):
    __tablename__ = TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    message = Column(JSONB, nullable=False)
    audio_url = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
