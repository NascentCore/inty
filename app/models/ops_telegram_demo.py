"""ORM for Ops Telegram demo bindings and shared-bot poll cursor."""

import sqlalchemy as sa
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class OpsTelegramDemoBinding(Base):
    """One Telegram DM bound to an Inty guest user + companion agent."""

    __tablename__ = "ops_telegram_demo_bindings"

    telegram_chat_id = Column(
        String,
        primary_key=True,
        comment="Telegram DM chat id; routing key for inbound getUpdates",
    )
    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        comment="Inty guest user for this Telegram account",
    )
    agent_id = Column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Companion agent_id for this binding",
    )
    chat_id = Column(
        String,
        ForeignKey("chats.id"),
        nullable=False,
        comment="Inty chat row id (MemoryStore scope)",
    )
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

    agent = relationship("Agent")


class OpsTelegramDemoPollState(Base):
    """Singleton row holding last Telegram getUpdates offset for the shared bot."""

    __tablename__ = "ops_telegram_demo_poll_state"

    id = Column(Integer, primary_key=True, comment="Fixed row id=1")
    last_update_id = Column(
        BigInteger,
        nullable=True,
        comment="Next getUpdates offset (update_id + 1 from last processed)",
    )
