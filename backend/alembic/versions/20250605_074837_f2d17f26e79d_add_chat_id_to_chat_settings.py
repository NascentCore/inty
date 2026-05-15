"""add_chat_id_to_chat_settings

Revision ID: f2d17f26e79d
Revises: d283e377e742
Create Date: 2025-06-05 07:48:37.262882+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2d17f26e79d'
down_revision: Union[str, None] = 'd283e377e742'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 chat_settings 表添加 chat_id 字段
    op.add_column('chat_settings', sa.Column('chat_id', sa.VARCHAR(), nullable=True))
    
    # 添加外键约束
    op.create_foreign_key(
        'fk_chat_settings_chat_id',
        'chat_settings', 'chats',
        ['chat_id'], ['id']
    )


def downgrade() -> None:
    # 删除外键约束
    op.drop_constraint('fk_chat_settings_chat_id', 'chat_settings', type_='foreignkey')
    
    # 删除 chat_id 字段
    op.drop_column('chat_settings', 'chat_id')
