"""creator_id nullable=false

Revision ID: 355ceb5017ff
Revises: 62b632b916ef
Create Date: 2025-09-27 03:45:07.016633+00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
# 修订标识符，由 Alembic 使用。
revision: str = '355ceb5017ff'
down_revision: Union[str, None] = '62b632b916ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# 如果creator_id为空，则设置为默认创建者ID
#这个用户ID是消耗的管理员默认用户ID，仓库系统配置必须时，使用scripts/init_admin_user。py读取数据库。
# 手动添加
    op.execute("UPDATE agents SET creator_id = 'user-01JWZ34Y4D1C92GD86A5R6EWYJ' WHERE creator_id IS NULL")
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.alter_column('agents', 'creator_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
# ### 结束 Alembic 命令 ###


def downgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.alter_column('agents', 'creator_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
# ### 结束 Alembic 命令 ###
