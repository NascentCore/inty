"""add run_at_date run_at_hour last_run_at to festival_memory_config

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-02-05 12:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "festival_memory_config",
        sa.Column(
            "run_at_date",
            sa.Date(),
            nullable=True,
            comment="执行日期，须 >= festival_date",
        ),
    )
    op.add_column(
        "festival_memory_config",
        sa.Column(
            "run_at_hour",
            sa.Integer(),
            nullable=True,
            comment="执行时刻 UTC 小时，0-23",
        ),
    )
    op.add_column(
        "festival_memory_config",
        sa.Column(
            "last_run_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近一次被定时任务执行的时间",
        ),
    )


def downgrade() -> None:
    op.drop_column("festival_memory_config", "last_run_at")
    op.drop_column("festival_memory_config", "run_at_hour")
    op.drop_column("festival_memory_config", "run_at_date")
