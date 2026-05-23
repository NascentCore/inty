"""add_discount_rate_to_subscription_plans

Revision ID: a1b2c3d4e5f6
Revises: 72a30085032d
Create Date: 2025-01-31 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "72a30085032d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加价格折扣率字段到订阅计划表"""
    op.add_column(
        "subscription_plans",
        sa.Column(
            "discount_rate",
            sa.Float(),
            nullable=False,
            server_default="1.0",
            comment="价格折扣率，范围0-1，1表示无折扣",
        ),
    )


def downgrade() -> None:
    """移除价格折扣率字段"""
    op.drop_column("subscription_plans", "discount_rate")
