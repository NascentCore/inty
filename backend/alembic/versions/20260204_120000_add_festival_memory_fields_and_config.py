"""add festival_name festival_date to memory and festival_memory_config table

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-02-04 12:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "memory",
        sa.Column(
            "festival_name",
            sa.String(),
            nullable=True,
            comment="节日名称，仅 memory_type=festival 时使用",
        ),
    )
    op.add_column(
        "memory",
        sa.Column(
            "festival_date",
            sa.Date(),
            nullable=True,
            comment="节日日期，仅 memory_type=festival 时使用",
        ),
    )

    op.create_table(
        "festival_memory_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "festival_name",
            sa.String(),
            nullable=False,
            comment="节日名称",
        ),
        sa.Column(
            "festival_date",
            sa.Date(),
            nullable=False,
            comment="节日日期",
        ),
        sa.Column(
            "prompt",
            sa.Text(),
            nullable=False,
            comment="抽取提示词",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="是否启用",
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
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("festival_memory_config")
    op.drop_column("memory", "festival_date")
    op.drop_column("memory", "festival_name")
