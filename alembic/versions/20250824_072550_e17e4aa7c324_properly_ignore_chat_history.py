"""test_include_object_working

Revision ID: e17e4aa7c324
Revises: 20250808_080000
Create Date: 2025-08-24 07:25:50.925856+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision: str = 'e17e4aa7c324'
down_revision: Union[str, None] = '20250808_080000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.alter_column('chat_settings', 'premium_mode',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_comment='高级模式开关，仅订阅用户可设置')
# ### 结束 Alembic 命令 ###


def downgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.alter_column('chat_settings', 'premium_mode',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_comment='高级模式开关，仅订阅用户可设置')
# ### 结束 Alembic 命令 ###
