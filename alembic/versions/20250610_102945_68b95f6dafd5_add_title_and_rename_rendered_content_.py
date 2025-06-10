"""add title and rename rendered_content to content in user_notifications

Revision ID: 68b95f6dafd5
Revises: 37c500eb8e24
Create Date: 2025-06-10 10:29:45.026066+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68b95f6dafd5'
down_revision: Union[str, None] = '37c500eb8e24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 添加 title 字段
    op.add_column('user_notifications', sa.Column('title', sa.Text(), nullable=True))
    
    # 2. 重命名 rendered_content 为 content
    op.alter_column('user_notifications', 'rendered_content', new_column_name='content')
    
    # 3. 将 content 字段设置为非空
    op.alter_column('user_notifications', 'content', nullable=False)


def downgrade() -> None:
    # 1. 将 content 字段重命名回 rendered_content
    op.alter_column('user_notifications', 'content', new_column_name='rendered_content')
    
    # 2. 删除 title 字段
    op.drop_column('user_notifications', 'title')
