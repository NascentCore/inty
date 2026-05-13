"""add feedback_push_history table

Revision ID: 20251203_100347
Revises: 20251202_141507
Create Date: 2025-12-03 10:03:47.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251203_100347"
down_revision: Union[str, None] = "20251202_141507"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_push_history",
        sa.Column("id", sa.String(), nullable=False, comment="推送记录ID"),
        sa.Column(
            "user_id",
            sa.String(),
            nullable=False,
            comment="用户ID",
        ),
        sa.Column(
            "chat_count_threshold",
            sa.Integer(),
            nullable=False,
            comment="触发的聊天轮数阈值（20/30/40/50/60）",
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="发送时间",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feedback_push_user_id"),
        "feedback_push_history",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feedback_push_sent_at"),
        "feedback_push_history",
        ["sent_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feedback_push_chat_count_threshold"),
        "feedback_push_history",
        ["chat_count_threshold"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_feedback_push_user_threshold",
        "feedback_push_history",
        ["user_id", "chat_count_threshold"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_feedback_push_user_threshold",
        "feedback_push_history",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_feedback_push_chat_count_threshold"),
        table_name="feedback_push_history",
    )
    op.drop_index(
        op.f("ix_feedback_push_sent_at"),
        table_name="feedback_push_history",
    )
    op.drop_index(
        op.f("ix_feedback_push_user_id"),
        table_name="feedback_push_history",
    )
    op.drop_table("feedback_push_history")

