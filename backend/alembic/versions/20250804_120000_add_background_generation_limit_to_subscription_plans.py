"""add_background_generation_limit_to_subscription_plans

Revision ID: 20250804_120000
Revises: 20250726_001000
Create Date: 2025-08-04 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250804_120000"
down_revision: Union[str, None] = "20250726_001000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add background_generation_limit_per_day column to subscription_plans table"""
    # 检查列是否已存在，如果不存在则添加
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='subscription_plans' 
        AND column_name='background_generation_limit_per_day'
    """))

    if not result.fetchone():
        # 添加 background_generation_limit_per_day 列
        op.add_column(
            "subscription_plans",
            sa.Column(
                "background_generation_limit_per_day",
                sa.Integer(),
                nullable=False,
                server_default="3",
                comment="每日背景图生成次数限制，-1为无限制",
            ),
        )

        # 更新现有订阅计划的背景图生成限制
        # 付费用户设置为无限制(-1)
        connection.execute(sa.text("""
            UPDATE subscription_plans 
            SET background_generation_limit_per_day = -1 
            WHERE id IN ('premium_monthly', 'premium_yearly')
        """))


def downgrade() -> None:
    """Remove background_generation_limit_per_day column from subscription_plans table"""
    # 检查列是否存在，如果存在则删除
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='subscription_plans' 
        AND column_name='background_generation_limit_per_day'
    """))

    if result.fetchone():
        op.drop_column(
            "subscription_plans", "background_generation_limit_per_day"
        )
