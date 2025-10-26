"""Remove first_message field from Agent model

Revision ID: 41ce4e778dd4
Revises: df2112660694
Create Date: 2025-07-23 09:16:14.453502+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision: str = '41ce4e778dd4'
down_revision: Union[str, None] = 'df2112660694'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# 从代理表中删除first_message列
    op.drop_column('agents', 'first_message')


def downgrade() -> None:
# 将first_message列重新添加到代理表中
    op.add_column('agents', sa.Column('first_message', sa.Text(), nullable=True))
