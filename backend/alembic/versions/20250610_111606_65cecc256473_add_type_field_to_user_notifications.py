"""add type field to user_notifications

Revision ID: 65cecc256473
Revises: 68b95f6dafd5
Create Date: 2025-06-10 11:16:06.312896+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "65cecc256473"
down_revision: Union[str, None] = "68b95f6dafd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 type 字段
    op.add_column(
        "user_notifications",
        sa.Column("type", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    # 删除 type 字段
    op.drop_column("user_notifications", "type")
