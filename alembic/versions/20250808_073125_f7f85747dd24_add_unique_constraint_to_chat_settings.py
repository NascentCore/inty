"""add_unique_constraint_to_chat_settings

Revision ID: f7f85747dd24
Revises: 43b18ddc9846
Create Date: 2025-08-08 07:31:25.068007+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7f85747dd24'
down_revision: Union[str, None] = '43b18ddc9846'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 首先清理重复的 chat_settings 数据
    # 对于每个 chat_id，只保留最新的那个设置记录
    op.execute("""
        DELETE FROM chat_settings 
        WHERE id NOT IN (
            SELECT DISTINCT ON (chat_id) id
            FROM chat_settings 
            ORDER BY chat_id, created_at DESC
        );
    """)
    
    # 创建唯一约束索引：每个聊天只能有一个设置记录
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_settings_chat_id 
        ON chat_settings (chat_id);
    """)


def downgrade() -> None:
    # 删除唯一索引
    op.execute("DROP INDEX IF EXISTS uq_chat_settings_chat_id;")
