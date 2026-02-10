"""add timezone to festival_memory_config

Revision ID: b9c8d7e6f5a4
Revises: a8b7c6d5e4f3
Create Date: 2026-02-10 12:00:00.000000+00:00

CREATED_BY_AGENT
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b9c8d7e6f5a4"
down_revision: Union[str, None] = "a8b7c6d5e4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "festival_memory_config",
        sa.Column(
            "timezone",
            sa.String(),
            nullable=False,
            server_default="UTC",
            comment="节日日期与执行时间所属时区，IANA 名如 Asia/Shanghai",
        ),
    )


def downgrade() -> None:
    op.drop_column("festival_memory_config", "timezone")
