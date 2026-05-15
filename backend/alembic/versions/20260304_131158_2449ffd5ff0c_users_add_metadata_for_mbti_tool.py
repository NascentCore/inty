"""users add metadata for mbti tool

Revision ID: 2449ffd5ff0c
Revises: 47eafda3e405
Create Date: 2026-03-04 13:11:58.470961+00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2449ffd5ff0c'
down_revision: Union[str, None] = '47eafda3e405'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "meta_data",
            sa.JSON(),
            nullable=True,
            comment="用户元数据（可扩展，例如 MBTI 类型）",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "meta_data")
