"""remove id column from resources table

Revision ID: 62b632b916ef
Revises: c1bbefc9d885
Create Date: 2025-09-26 07:11:30.105213+00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
# 修订标识符，由 Alembic 使用。
revision: str = '62b632b916ef'
down_revision: Union[str, None] = 'c1bbefc9d885'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.alter_column('resources', 'url',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_index(op.f('ix_resources_id'), table_name='resources')
    op.create_index(op.f('ix_resources_url'), 'resources', ['url'], unique=False)
    op.drop_column('resources', 'id')
# ### 结束 Alembic 命令 ###


def downgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
#首先将id列添加为补充空
    op.add_column('resources', sa.Column('id', sa.VARCHAR(), autoincrement=False, nullable=True))
# 使用 url 中的值填充 id 列（因为 url 现在是 primary 键）
    op.execute("UPDATE resources SET id = url")
# 现在使id列不为空
    op.alter_column('resources', 'id', nullable=False)
    
    op.drop_index(op.f('ix_resources_url'), table_name='resources')
    op.create_index(op.f('ix_resources_id'), 'resources', ['id'], unique=False)
    op.alter_column('resources', 'url',
               existing_type=sa.VARCHAR(),
               nullable=True)
# ### 结束 Alembic 命令 ###
