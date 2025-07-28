"""Add background_generation_limit_per_day to subscription_plans

Revision ID: add_bg_limit_001
Revises: 41ce4e778dd4
Create Date: 2025-07-28 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_bg_limit_001'
down_revision: Union[str, None] = '41ce4e778dd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add background_generation_limit_per_day column to subscription_plans table
    op.add_column('subscription_plans', sa.Column('background_generation_limit_per_day', sa.Integer(), nullable=True, comment='每日背景图生成次数限制，-1为无限制'))
    
    # Set default value for existing records
    op.execute("UPDATE subscription_plans SET background_generation_limit_per_day = 3 WHERE background_generation_limit_per_day IS NULL")
    
    # Make the column not nullable after setting default values
    op.alter_column('subscription_plans', 'background_generation_limit_per_day', nullable=False)


def downgrade() -> None:
    # Remove background_generation_limit_per_day column from subscription_plans table
    op.drop_column('subscription_plans', 'background_generation_limit_per_day')