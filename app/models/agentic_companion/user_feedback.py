"""User-feedback persistence for the agentic companion maintenance track.

The companion infers feedback about its own behavior from the recent conversation
during an inner-tick maintenance turn and records it here with enough reproduction
context (scope ids + ``trace_id``/``user_msg_uuid`` of the recording run + verbatim
quotes) to trace it back to the triggering conversation and its LangSmith run.
"""

from __future__ import annotations

from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, JSON, String, Text
from pydantic import BaseModel, Field

from app.models.base import Base

RECORD_USER_FEEDBACK_TOOL_NAME = "record_user_feedback"


class UserFeedbackCategory(StrEnum):
    """Coarse bucket for companion-behavior feedback, kept queryable as a column."""

    TALKS_TOO_MUCH = "talks_too_much"
    TOO_REPETITIVE = "too_repetitive"
    TONE = "tone"
    PERSONA_MISMATCH = "persona_mismatch"
    RESPONSE_QUALITY = "response_quality"
    OTHER = "other"


class UserFeedbackReproContext(BaseModel):
    """Conversation anchors persisted in the ``repro_context`` JSON column."""

    user_quote: str | None = Field(
        default=None,
        description="Verbatim user words from the window that evidence the feedback.",
    )
    offending_assistant_text: str | None = Field(
        default=None,
        description="The companion reply the feedback is about, if identifiable.",
    )


class CompanionUserFeedback(Base):
    """One inferred feedback row about the companion's behavior (append-only)."""

    __tablename__ = "companion_user_feedback"

    id = Column(String(64), primary_key=True, comment="反馈记录ID (uuid hex)")
    user_id = Column(String, nullable=False, index=True, comment="用户ID")
    companion_id = Column(
        String, nullable=False, index=True, comment="伴侣/Agent ID"
    )
    chat_id = Column(String, nullable=False, comment="会话ID")
    category = Column(
        String(64), nullable=False, comment="UserFeedbackCategory 枚举值"
    )
    feedback_text = Column(
        Text, nullable=False, comment="跨多条消息推断出的反馈摘要"
    )
    trace_id = Column(
        String(64),
        nullable=True,
        index=True,
        comment="记录该反馈的 inner-tick 运行的 Inty trace_id",
    )
    user_msg_uuid = Column(
        String(64), nullable=True, comment="记录运行关联的 user_msg_uuid"
    )
    repro_context = Column(
        JSON,
        nullable=True,
        comment="UserFeedbackReproContext: 用户原话与相关回复等复现锚点",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=sa.text("now()"),
        comment="创建时间",
    )
