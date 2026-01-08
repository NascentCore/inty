"""users 表增加 user_photo 字段

Revision ID: 83f37ed3d576
Revises: 03cab396adc0
Create Date: 2026-01-08 17:25:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "83f37ed3d576"
down_revision: Union[str, None] = "03cab396adc0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "user_photo",
            sa.String(),
            nullable=True,
            comment="用户自拍照片URL，用于生图参考",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "user_photo")
