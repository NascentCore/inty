"""Companion MemoryStore document versions (append-only, ORM-backed Postgres)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, DateTime, Index, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class CompanionMemoryDocumentVersion(Base):
    """
    One row per append of a logical document for (user, companion, chat).

    Natural key for the latest body: (user_id, companion_id, chat_id, document_kind,
    calendar_date) with max(sequence_id).
    """

    __tablename__ = "companion_memory_document_versions"

    sequence_id = Column(BigInteger, primary_key=True, autoincrement=True)
    record_uuid = Column(String(64), nullable=False, unique=True)
    user_id = Column(String, nullable=False)
    companion_id = Column(String, nullable=False)
    chat_id = Column(String, nullable=False)
    document_kind = Column(String(64), nullable=False)
    calendar_date = Column(Date, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_companion_memory_doc_scope_kind_date_seq",
            "user_id",
            "companion_id",
            "chat_id",
            "document_kind",
            "calendar_date",
            "sequence_id",
        ),
    )
