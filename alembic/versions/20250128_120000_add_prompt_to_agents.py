"""add prompt to agents

Revision ID: add_prompt_to_agents
Revises: 109ce7b3713c
Create Date: 2025-01-28 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision: str = 'add_prompt_to_agents'
down_revision: Union[str, None] = '109ce7b3713c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.add_column('agents', sa.Column('prompt', sa.String(), nullable=True))
# ### 结束 Alembic 命令 ###


def downgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.drop_column('agents', 'prompt')
# ### 结束 Alembic 命令 ###