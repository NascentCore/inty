"""add ops_telegram_demo_bindings and poll_state tables

Revision ID: 20260612_120000
Revises: f73e1b518bfe
Create Date: 2026-06-12 12:00:00+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_120000"
down_revision: Union[str, None] = "f73e1b518bfe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_POLL_STATE_ID = 1


def upgrade() -> None:
    op.create_table(
        "ops_telegram_demo_bindings",
        sa.Column(
            "telegram_chat_id",
            sa.String(),
            nullable=False,
            comment="Telegram DM chat id; routing key for inbound getUpdates",
        ),
        sa.Column(
            "user_id",
            sa.String(),
            nullable=False,
            comment="Inty guest user for this Telegram account",
        ),
        sa.Column(
            "agent_id",
            sa.String(),
            nullable=False,
            comment="Companion agent_id for this binding",
        ),
        sa.Column(
            "chat_id",
            sa.String(),
            nullable=False,
            comment="Inty chat row id (MemoryStore scope)",
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
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("telegram_chat_id"),
    )
    op.create_table(
        "ops_telegram_demo_poll_state",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
            comment="Fixed row id=1",
        ),
        sa.Column(
            "last_update_id",
            sa.BigInteger(),
            nullable=True,
            comment="Next getUpdates offset (update_id + 1 from last processed)",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO ops_telegram_demo_poll_state (id, last_update_id) "
            f"VALUES ({_POLL_STATE_ID}, NULL)"
        )
    )


def downgrade() -> None:
    op.drop_table("ops_telegram_demo_poll_state")
    op.drop_table("ops_telegram_demo_bindings")
