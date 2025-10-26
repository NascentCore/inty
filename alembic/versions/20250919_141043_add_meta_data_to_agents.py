"""add_meta_data_to_agents

Revision ID: add_meta_data_to_agents
Revises: 31cde68a9b0a
Create Date: 2025-09-19 14:10:43.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
# 修订标识符，由 Alembic 使用。
revision: str = 'add_meta_data_to_agents'
down_revision: Union[str, None] = '31cde68a9b0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# 检查meta_data列是否已经存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('agents')]
    
    if 'meta_data' not in columns:
        op.add_column('agents', sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        print("Added meta_data column to agents table")
    else:
        print("meta_data column already exists in agents table, skipping")


def downgrade() -> None:
#删除前检查meta_data列是否存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('agents')]
    
    if 'meta_data' in columns:
        op.drop_column('agents', 'meta_data')
        print("Dropped meta_data column from agents table")
    else:
        print("meta_data column does not exist in agents table, skipping")