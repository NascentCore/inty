"""add_opening_audio_url_to_agents

Revision ID: ab7f71ad458d
Revises: 75796d073cb2
Create Date: 2025-09-09 07:15:51.549799+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision: str = 'ab7f71ad458d'
down_revision: Union[str, None] = '75796d073cb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
# 检查 opening_audio_url 列是否已存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('agents')]
    
    if 'opening_audio_url' not in columns:
        op.add_column('agents', sa.Column('opening_audio_url', sa.String(), nullable=True))
        print("Added opening_audio_url column to agents table")
    else:
        print("opening_audio_url column already exists in agents table, skipping")
# ### 结束 Alembic 命令 ###


def downgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
# 在删除前检查 opening_audio_url 列是否存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('agents')]
    
    if 'opening_audio_url' in columns:
        op.drop_column('agents', 'opening_audio_url')
        print("Dropped opening_audio_url column from agents table")
    else:
        print("opening_audio_url column does not exist in agents table, skipping")
# ### 结束 Alembic 命令 ###
