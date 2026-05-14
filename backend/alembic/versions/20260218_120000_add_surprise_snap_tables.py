"""add surprise_snap progress and unlock tables

Revision ID: e5f6a7b8c9d1
Revises: d4e5f6a7b8c0
Create Date: 2026-02-18 12:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d1"
down_revision: Union[str, None] = "d4e5f6a7b8c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "surprise_snap_progress",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("next_photo_index", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "agent_id", name="uq_surprise_snap_progress_user_agent"
        ),
    )
    op.create_index(
        "ix_surprise_snap_progress_user_id",
        "surprise_snap_progress",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_surprise_snap_progress_agent_id",
        "surprise_snap_progress",
        ["agent_id"],
        unique=False,
    )

    op.create_table(
        "surprise_snap_unlock",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"], ["chat_history.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "message_id", name="uq_surprise_snap_unlock_user_message"
        ),
    )
    op.create_index(
        "ix_surprise_snap_unlock_user_id",
        "surprise_snap_unlock",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_surprise_snap_unlock_message_id",
        "surprise_snap_unlock",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_surprise_snap_unlock_message_id", table_name="surprise_snap_unlock"
    )
    op.drop_index("ix_surprise_snap_unlock_user_id", table_name="surprise_snap_unlock")
    op.drop_table("surprise_snap_unlock")
    op.drop_index(
        "ix_surprise_snap_progress_agent_id", table_name="surprise_snap_progress"
    )
    op.drop_index(
        "ix_surprise_snap_progress_user_id", table_name="surprise_snap_progress"
    )
    op.drop_table("surprise_snap_progress")
