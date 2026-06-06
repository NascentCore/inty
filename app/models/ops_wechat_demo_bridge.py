"""ORM for Ops WeChat demo bridge rows (Weixin↔Inty relay state, crash-resume)."""

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class OpsWechatDemoBridge(Base):
    """One bridge row: persisted Weixin↔Inty relay for a demo session after QR login.

    **Bridge** = ``WeixinChannelSession`` runtime (Hermes bot + Inty companion WS), not
    the QR-login orchestration. Row exists while bridge is running; deleted on
    stop/fail. ``session_id`` is primary key and ``WeixinChannelBinding.user_id``.

    ``weixin_token``: iLink bot_token after QR; no protocol TTL — ends at errcode=-14.

    TODO(wechat-demo-bridge-fk): evaluate agent_id FK ON DELETE CASCADE semantics.
    TODO(wechat-demo-bridge-jwt): restore/persist remint in bridge_jwt; see
    TODO(wechat-demo-bridge-jwt-periodic) for long-running bridges without DM.
    """

    __tablename__ = "ops_wechat_demo_bridges"

    session_id = Column(
        String,
        primary_key=True,
        comment="Ops demo session UUID; WeixinChannelBinding.user_id",
    )
    inty_api_base_url = Column(
        String,
        nullable=False,
        comment="Inty HTTP API origin for companion WebSocket",
    )
    inty_jwt = Column(
        Text,
        nullable=False,
        comment="Bearer JWT for Inty WS auth (plaintext Ops demo)",
    )
    agent_id = Column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Inty companion agent_id on the WebSocket",
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
