"""ORM for agentic companion durable input/output queues."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from app.models.base import Base


class AgenticCompanionInputQueueRow(Base):
    """One inbound user message awaiting AgenticCompanion drain."""

    __tablename__ = "agentic_companion_input_queue"
    __table_args__ = (
        Index(
            "ix_agentic_companion_input_queue_scope_status_seq",
            "user_id",
            "agent_id",
            "status",
            "sequence_id",
        ),
    )

    id = Column(
        String,
        primary_key=True,
        comment="Queue message id (uuid)",
    )
    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        comment="Inty human user id",
    )
    agent_id = Column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Inty companion agent id",
    )
    sequence_id = Column(
        BigInteger,
        sa.Identity(),
        nullable=False,
        comment="Monotonic ordering within scope",
    )
    status = Column(
        String,
        nullable=False,
        comment="QueueStatus value",
    )
    channel = Column(
        String,
        nullable=False,
        comment="CompanionRuntimeChannel value",
    )
    wire_id = Column(
        String,
        nullable=False,
        comment="Opaque runtime wire id",
    )
    client_message_id = Column(
        String,
        nullable=True,
        comment="Client-supplied message id when available",
    )
    text = Column(
        Text,
        nullable=False,
        comment="User-visible inbound text",
    )
    batch_id = Column(
        String,
        nullable=True,
        comment="Claim batch id when claimed by AgenticCompanion",
    )
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
        nullable=False,
    )


class AgenticCompanionOutputQueueRow(Base):
    """One agent output awaiting active Channel/Wire delivery."""

    __tablename__ = "agentic_companion_output_queue"
    __table_args__ = (
        Index(
            "ix_agentic_companion_output_queue_scope_status_seq",
            "user_id",
            "agent_id",
            "status",
            "sequence_id",
        ),
        Index(
            "ix_agentic_companion_output_queue_batch_seq",
            "batch_id",
            "sequence_id",
        ),
    )

    id = Column(
        String,
        primary_key=True,
        comment="Queue message id (uuid)",
    )
    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        comment="Inty human user id",
    )
    agent_id = Column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Inty companion agent id",
    )
    sequence_id = Column(
        BigInteger,
        sa.Identity(),
        nullable=False,
        comment="Monotonic ordering within scope",
    )
    status = Column(
        String,
        nullable=False,
        comment="QueueStatus value",
    )
    batch_id = Column(
        String,
        nullable=False,
        comment="Input batch or synthetic turn batch id",
    )
    kind = Column(
        String,
        nullable=False,
        comment="DownlinkKind value",
    )
    text = Column(
        Text,
        nullable=False,
        comment="Assistant-visible text payload",
    )
    in_reply_to_input_ids_json = Column(
        Text,
        nullable=False,
        server_default=sa.text("'[]'"),
        comment="JSON array of input queue ids",
    )
    trace_id = Column(String, nullable=True)
    langsmith_trace_id = Column(String, nullable=True)
    langsmith_run_id = Column(String, nullable=True)
    turn_recall = Column(Text, nullable=True)
    delivery_channel = Column(String, nullable=True)
    delivery_wire_id = Column(String, nullable=True)
    delivery_attempt_count = Column(Integer, nullable=False, server_default="0")
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
        nullable=False,
    )
