"""subscription_usage 表增加 (user_id, usage_type, usage_date) 复合索引，供记忆抽取筛选查询

Revision ID: a8b7c6d5e4f3
Revises: f2a3b4c5d6e7
Create Date: 2026-02-06 12:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a8b7c6d5e4f3"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_subscription_usage_user_type_date",
        "subscription_usage",
        ["user_id", "usage_type", "usage_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscription_usage_user_type_date",
        table_name="subscription_usage",
    )
