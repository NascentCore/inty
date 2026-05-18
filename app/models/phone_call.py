"""Phone-call caller bindings used to resolve inbound PSTN calls."""

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class PhoneCallCallerBinding(Base):
    """A privacy-preserving caller-number binding for inbound PSTN calls."""

    __tablename__ = "phone_call_caller_bindings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    phone_number_hmac = Column(String(64), nullable=False, unique=True)
    phone_number_masked = Column(String(32), nullable=False)
    last_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"))
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    user = relationship("User")
    agent = relationship("Agent")

    __table_args__ = (
        Index("ix_phone_call_caller_bindings_user_id", "user_id"),
        Index("ix_phone_call_caller_bindings_phone_hmac", "phone_number_hmac"),
    )
