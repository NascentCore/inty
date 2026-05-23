"""add memory and memory_extraction_log tables

Revision ID: a7b8c9d0e1f2
Revises: 01e2b25d0aa8
Create Date: 2026-01-27 12:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "01e2b25d0aa8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "memory_type",
            sa.String(),
            nullable=False,
            comment="user_common | user_agent",
        ),
        sa.Column(
            "agent_id",
            sa.String(),
            nullable=True,
            comment="user_common 为 NULL",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="单条记忆内容，当前 Part1 整段存为一条",
        ),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="所属抽取批次时间",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memory_user_type",
        "memory",
        ["user_id", "memory_type"],
        unique=False,
    )
    op.create_index(
        "ix_memory_user_type_agent",
        "memory",
        ["user_id", "memory_type", "agent_id"],
        unique=False,
    )

    op.create_table(
        "memory_extraction_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("messages_processed_count", sa.Integer(), nullable=False),
        sa.Column("memory_items_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            comment="success | partial | failed",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memory_extraction_log_user_type",
        "memory_extraction_log",
        ["user_id", "memory_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_memory_extraction_log_user_type", table_name="memory_extraction_log"
    )
    op.drop_table("memory_extraction_log")
    op.drop_index("ix_memory_user_type_agent", table_name="memory")
    op.drop_index("ix_memory_user_type", table_name="memory")
    op.drop_table("memory")
