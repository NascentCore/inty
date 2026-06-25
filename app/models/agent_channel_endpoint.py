"""ORM for agent-channel endpoint bindings (multi-medium, no legacy chats row).

TODO(rename-channel-to-gateway): Store ``ChannelKind`` wire values; optional model/table — #3548
rename is out of scope for #3548 — track separately if needed.
"""

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class AgentChannelEndpoint(Base):
    """One bonded channel endpoint for an ``(user_id, agent_id)`` scope.

    TODO(telegram-dedicated-bot-bonding): Per-endpoint bot token / bot_id for Option B —
    #3361 (epic #3395); shared-bot Option A — #3396
    """

    __tablename__ = "agent_channel_endpoints"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "channel_address",
            name="uq_agent_channel_endpoints_channel_address",
        ),
        UniqueConstraint(
            "channel",
            "channel_user_id",
            name="uq_agent_channel_endpoints_channel_user_id",
        ),
        UniqueConstraint(
            "user_id",
            "channel",
            name="uq_agent_channel_endpoints_user_channel",
        ),
        UniqueConstraint(
            "agent_id",
            "channel",
            name="uq_agent_channel_endpoints_agent_channel",
        ),
    )

    id = Column(
        String,
        primary_key=True,
        comment="Endpoint row id (uuid)",
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
    channel = Column(
        String,
        nullable=False,
        comment="CompanionRuntimeChannel value (telegram, wechat_weixin, …)",
    )
    channel_address = Column(
        String,
        nullable=False,
        comment="Opaque outbound routing key on this channel",
    )
    channel_user_id = Column(
        String,
        nullable=False,
        comment="Opaque channel-side human identity for 1:1 bonding",
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
