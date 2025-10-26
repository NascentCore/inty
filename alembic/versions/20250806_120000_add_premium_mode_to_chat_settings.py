"""Add premium_mode to chat_settings

Revision ID: 20250806_120000
Revises: a1935acfeee0
Create Date: 2025-08-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision = '20250806_120000'
down_revision = 'a1935acfeee0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add premium_mode column to chat_settings table"""
# 检查该列是否已经存在
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('chat_settings')]
    
    if 'premium_mode' not in columns:
#首先将列添加为空
        op.add_column('chat_settings', sa.Column('premium_mode', sa.Boolean(), nullable=True, comment='高级模式开关，仅订阅用户可设置'))
# 更新现有行以设置默认值
        connection.execute(sa.text("UPDATE chat_settings SET premium_mode = false WHERE premium_mode IS NULL"))
#使该列不可为空
        op.alter_column('chat_settings', 'premium_mode', nullable=False)


def downgrade() -> None:
    """Remove premium_mode column from chat_settings table"""
# 在尝试删除该列之前检查该列是否存在
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('chat_settings')]
    
    if 'premium_mode' in columns:
        op.drop_column('chat_settings', 'premium_mode')