"""add background_images to agents

Revision ID: 20250129_130000
Revises: 14fb99385272
Create Date: 2025-01-29 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250129_130000'
down_revision = '14fb99385272'
branch_labels = None
depends_on = None


def upgrade():
    # 为agents表添加background_images字段
    op.add_column('agents', sa.Column('background_images', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    # 移除background_images字段
    op.drop_column('agents', 'background_images') 