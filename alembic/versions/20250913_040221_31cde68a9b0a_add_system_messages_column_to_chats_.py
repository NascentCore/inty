"""add_system_messages_column_to_chats_table

Revision ID: 31cde68a9b0a
Revises: 5e2d9282c49c
Create Date: 2025-09-13 04:02:21.306726+00:00

"""
from typing import Sequence, Union

from alembic import op
# 修订标识符，由 Alembic 使用。
revision: str = '31cde68a9b0a'
down_revision: Union[str, None] = '5e2d9282c49c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.drop_index(op.f('idx_chat_history_session_id'), table_name='chat_history')
    op.create_index(op.f('ix_chat_history_session_id'), 'chat_history', ['session_id'], unique=False)
# ### 结束 Alembic 命令 ###


def downgrade() -> None:
# ### 由 Alembic 自动生成的命令 - 请调整！###
    op.drop_index(op.f('ix_chat_history_session_id'), table_name='chat_history')
    op.create_index(op.f('idx_chat_history_session_id'), 'chat_history', ['session_id'], unique=False)
# ### 结束 Alembic 命令 ###
