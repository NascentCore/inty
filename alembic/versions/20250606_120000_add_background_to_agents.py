"""add_background_to_agents

Revision ID: 20250606_120000
Revises: 24a617b81c38
Create Date: 2025-06-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision = '20250606_120000'
down_revision = '24a617b81c38'
branch_labels = None
depends_on = None


def upgrade():
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.add_column('agents', sa.Column('background', sa.String(), nullable=True))
# ### 结束 Alembic 命令 ###


def downgrade():
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.drop_column('agents', 'background')
# ### 结束 Alembic 命令 ###