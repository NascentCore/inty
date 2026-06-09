"""ORM for Ops Weixin bridge rows (Weixin↔Inty relay state, crash-resume)."""

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class OpsWeixinBridge(Base):
    """One bridge row: persisted Weixin↔Inty relay after QR onboard.

    **Bridge** = ``WeixinChannelSession`` runtime (Hermes bot + in-process companion), not
    the QR-login orchestration. Row exists while bridge is running; deleted on
    stop/fail. ``session_id`` is primary key and ``WeixinChannelBinding.user_id``.

    ``weixin_token``: iLink bot_token after QR; no protocol TTL — ends at errcode=-14.

    TODO(weixin-bridge-fk): evaluate agent_id FK ON DELETE CASCADE semantics.
    TODO(weixin-bridge-jwt): inty_jwt is static Bearer from onboard provision; needs
    user-auth binding + refresh — see plan Follow-up TODO.
    """

    __tablename__ = "ops_wechat_demo_bridges"

    session_id = Column(
        String,
        primary_key=True,
        comment="Ops Weixin session UUID; WeixinChannelBinding.user_id",
    )
    inty_api_base_url = Column(
        String,
        nullable=False,
        comment="Inty HTTP API origin for companion",
    )
    inty_jwt = Column(
        Text,
        nullable=False,
        comment="Bearer JWT for Inty companion auth",
    )
    agent_id = Column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Inty companion agent_id",
    )
    weixin_account_id = Column(
        String,
        nullable=False,
        comment="iLink Weixin bot account id",
    )
    weixin_token = Column(
        Text,
        nullable=False,
        comment=(
            "iLink bot_token after QR; no API TTL — invalid when errcode=-14 on poll/send"
        ),
    )
    weixin_base_url = Column(
        String,
        nullable=False,
        comment="iLink API base URL",
    )
    last_peer_id = Column(
        String,
        nullable=True,
        comment="Most recent inbound WeChat DM peer_id for proactive downlink",
    )
    last_peer_seen_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC time when last_peer_id last sent inbound",
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
