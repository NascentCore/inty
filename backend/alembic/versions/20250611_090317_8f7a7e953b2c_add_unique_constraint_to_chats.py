"""add_unique_constraint_to_chats

Revision ID: 8f7a7e953b2c
Revises: 65cecc256473
Create Date: 2025-06-11 09:03:17.123456+00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8f7a7e953b2c'
down_revision: Union[str, None] = '65cecc256473'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 首先清理重复数据
    # 对于每个(user_id, agent_id)组合，只保留最新的那个活跃记录
    op.execute("""
        UPDATE chats SET is_active = false 
        WHERE id NOT IN (
            SELECT DISTINCT ON (user_id, agent_id) id
            FROM chats 
            WHERE is_active = true
            ORDER BY user_id, agent_id, created_at DESC
        ) AND is_active = true;
    """)
    
    # 使用原生SQL添加部分唯一约束：每个用户与每个Agent只能有一个活跃的聊天会话
    op.execute("""
        CREATE UNIQUE INDEX uq_chats_user_agent_active 
        ON chats (user_id, agent_id) 
        WHERE is_active = true;
    """)


def downgrade() -> None:
    # 删除唯一索引
    op.execute("DROP INDEX IF EXISTS uq_chats_user_agent_active;")
