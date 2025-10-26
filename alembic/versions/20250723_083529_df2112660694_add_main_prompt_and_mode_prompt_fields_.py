"""Add main_prompt and mode_prompt fields to Agent model

Revision ID: df2112660694
Revises: 20250718_014000
Create Date: 2025-07-23 08:35:29.789603+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision: str = 'df2112660694'
down_revision: Union[str, None] = '20250718_014000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# 将 main_prompt 列添加到代理表中
    op.add_column('agents', sa.Column('main_prompt', sa.Text(), nullable=True))
# 将模式__prompt 列添加到代理表中
    op.add_column('agents', sa.Column('mode_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
# 从代理表中删除模式__prompt 列
    op.drop_column('agents', 'mode_prompt')
# 从代理表中删除 main_prompt 列
    op.drop_column('agents', 'main_prompt')
