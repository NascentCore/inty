"""add min_rounds_in_window to festival_memory_config

Revision ID: c0d9e8f7a6b5
Revises: b9c8d7e6f5a4
Create Date: 2026-02-11 12:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c0d9e8f7a6b5"
down_revision: Union[str, None] = "b9c8d7e6f5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "festival_memory_config",
        sa.Column(
            "min_rounds_in_window",
            sa.Integer(),
            nullable=True,
            comment="窗口内最少用户消息轮数，NULL 表示默认 15",
        ),
    )


def downgrade() -> None:
    op.drop_column("festival_memory_config", "min_rounds_in_window")
