"""drop memory.festival_name and memory.festival_date

节日名称/日期已仅存于 memory.metadata (meta_data)，旧列移除。

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
Create Date: 2026-02-17 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b9"
down_revision: Union[str, None] = "b2c3d4e5f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("memory", "festival_date")
    op.drop_column("memory", "festival_name")


def downgrade() -> None:
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
