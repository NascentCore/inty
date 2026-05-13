"""add background_animated to agents

Revision ID: 20250130_120000
Revises: f5d4815312ac
Create Date: 2025-01-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250130_120000'
down_revision = 'f5d4815312ac'
branch_labels = None
depends_on = None


def upgrade():
    # 为agents表添加background_animated字段，用于存储AVIF或GIF格式的动图URL
    op.add_column('agents', sa.Column('background_animated', sa.String(), nullable=True))


def downgrade():
    # 移除background_animated字段
    op.drop_column('agents', 'background_animated')

