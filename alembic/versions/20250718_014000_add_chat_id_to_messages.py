"""Add chat_id to messages table if not exists

Revision ID: 20250718_014000
Revises: 20250718_012500
Create Date: 2025-07-18 01:40:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision: str = '20250718_014000'
down_revision: Union[str, None] = '20250718_012500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
#检查chat_id列是否存在，如果不存在则添加
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('messages')]
    
    if 'chat_id' not in columns:
# 将chat_id列添加到消息表中
        op.add_column('messages', sa.Column('chat_id', sa.String(), nullable=True))
#添加外键约束
        op.create_foreign_key(
            'fk_messages_chat_id',
            'messages', 'chats',
            ['chat_id'], ['id']
        )


def downgrade() -> None:
# 在尝试删除之前检查chat_id列是否存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('messages')]
    
    if 'chat_id' in columns:
#首先删除外键约束
        op.drop_constraint('fk_messages_chat_id', 'messages', type_='foreignkey')
#删除该列
        op.drop_column('messages', 'chat_id')