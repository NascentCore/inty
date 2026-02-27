"""add delivery_at to memory table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-02-13 12:00:00.000000+00:00

节日记忆按需投递：memory 表增加 delivery_at，表示节日记忆提示首次投递到会话的时间。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "memory",
        sa.Column(
            "delivery_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="节日记忆提示首次投递到会话的时间，仅 memory_type=festival 时使用",
        ),
    )


def downgrade() -> None:
    op.drop_column("memory", "delivery_at")
