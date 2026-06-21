"""ORM for explicit user-companion active bond state."""

from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class CompanionBondState(StrEnum):
    """Lifecycle state for one user-companion relationship bond."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanionBond(Base):
    """Persistent source of truth for one human user bonded to one companion."""

    __tablename__ = "companion_bonds"

    id = Column(
        String,
        primary_key=True,
        comment="Bond row id (uuid)",
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
    state = Column(
        Enum(CompanionBondState, name="companionbondstate"),
        nullable=False,
        comment="CompanionBondState value",
    )
    inactive_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this bond stopped being active",
    )
    runtime_paused_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this active bond's runtime was paused for cost control",
    )
    last_resumed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this active bond's runtime was last resumed",
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

    user = relationship("User")
    agent = relationship("Agent")
