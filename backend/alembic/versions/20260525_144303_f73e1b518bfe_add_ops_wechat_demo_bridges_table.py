"""add ops_wechat_demo_bridges table

Revision ID: f73e1b518bfe
Revises: 20260512_phone_call_bindings
Create Date: 2026-05-25 14:43:03.370931+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f73e1b518bfe'
down_revision: Union[str, None] = '20260512_phone_call_bindings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ops_wechat_demo_bridges",
        sa.Column(
            "session_id",
            sa.String(),
            nullable=False,
            comment="Ops demo session UUID; WeixinChannelBinding.user_id",
        ),
        sa.Column(
            "inty_api_base_url",
            sa.String(),
            nullable=False,
            comment="Inty HTTP API origin for companion WebSocket",
        ),
        sa.Column(
            "inty_jwt",
            sa.Text(),
            nullable=False,
            comment="Bearer JWT for Inty WS auth (plaintext Ops demo)",
        ),
        sa.Column(
            "agent_id",
            sa.String(),
            nullable=False,
            comment="Inty companion agent_id on the WebSocket",
        ),
        sa.Column(
            "weixin_account_id",
            sa.String(),
            nullable=False,
            comment="iLink Weixin bot account id",
        ),
        sa.Column(
            "weixin_token",
            sa.Text(),
            nullable=False,
            comment="iLink bot token (inline for restore without hermes files)",
        ),
        sa.Column(
            "weixin_base_url",
            sa.String(),
            nullable=False,
            comment="iLink API base URL",
        ),
        sa.Column(
            "last_peer_id",
            sa.String(),
            nullable=True,
            comment="Most recent inbound WeChat DM peer_id for proactive downlink",
        ),
        sa.Column(
            "last_peer_seen_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="UTC time when last_peer_id last sent inbound",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )


def downgrade() -> None:
    op.drop_table('ops_wechat_demo_bridges')
