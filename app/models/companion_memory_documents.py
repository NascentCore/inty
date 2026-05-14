"""Companion MemoryStore document versions (append-only, ORM-backed Postgres)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, DateTime, Index, String, Text
from sqlalchemy.sql import func, text

from app.models.base import Base


class CompanionMemoryDocumentVersion(Base):
    """
    One row per append of a logical document for (user, companion, chat).

    Logical body is folded from all rows for the scope key in ``sequence_id`` order:
    ``snapshot`` replaces the accumulated body; ``suffix`` concatenates to it.
    """

    __tablename__ = "companion_memory_document_versions"

    sequence_id = Column(BigInteger, primary_key=True, autoincrement=True)
    record_uuid = Column(String(64), nullable=False, unique=True)
    user_id = Column(String, nullable=False)
    companion_id = Column(String, nullable=False)
    chat_id = Column(String, nullable=False)
    document_kind = Column(String(64), nullable=False)
    calendar_date = Column(Date, nullable=True)
    content_mode = Column(String(16), nullable=False, server_default=text("'snapshot'"))
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
