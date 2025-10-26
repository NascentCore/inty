"""make_creator_id_nullable

Revision ID: 959ca996a9d7
Revises: add_prompt_to_agents
Create Date: 2025-06-05 05:26:39.941883+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision: str = '959ca996a9d7'
down_revision: Union[str, None] = 'add_prompt_to_agents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
# 修改creator_id 字段允许为空
    op.alter_column('agents', 'creator_id',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
# ### 结束 Alembic 命令 ###


def downgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
#还原creator_id字段为允许为空
    op.alter_column('agents', 'creator_id',
                    existing_type=sa.VARCHAR(),
                    nullable=False)
# ### 结束 Alembic 命令 ###
