"""add duration to voice cache

Revision ID: c1bbefc9d885
Revises: add_meta_data_to_agents
Create Date: 2025-09-23 05:48:21.088278+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
# 修订标识符，由 Alembic 使用。
revision: str = 'c1bbefc9d885'
down_revision: Union[str, None] = 'add_meta_data_to_agents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.alter_column('agents', 'meta_data',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=sa.JSON(),
               existing_nullable=True)
    op.add_column('voice_cache', sa.Column('duration', sa.Float(), nullable=True))
# ### 结束 Alembic 命令 ###


def downgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.drop_column('voice_cache', 'duration')
    op.alter_column('agents', 'meta_data',
               existing_type=sa.JSON(),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True)
# ### 结束 Alembic 命令 ###
