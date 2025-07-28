"""Create system_settings table

Revision ID: system_settings_001
Revises: add_bg_limit_001
Create Date: 2025-07-28 13:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'system_settings_001'
down_revision: Union[str, None] = 'add_bg_limit_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create system_settings table
    op.create_table('system_settings',
        sa.Column('key', sa.String(length=100), nullable=False, comment='配置键名'),
        sa.Column('value', sa.Text(), nullable=False, comment='配置值'),
        sa.Column('value_type', sa.Enum('STRING', 'INTEGER', 'FLOAT', 'BOOLEAN', 'JSON', name='settingtype'), nullable=False, comment='值类型'),
        sa.Column('category', sa.Enum('SUBSCRIPTION_LIMITS', 'SYSTEM_FEATURES', 'SECURITY', 'GENERAL', name='settingcategory'), nullable=False, comment='配置分类'),
        sa.Column('description', sa.Text(), nullable=True, comment='配置描述'),
        sa.Column('default_value', sa.Text(), nullable=True, comment='默认值'),
        sa.Column('is_system', sa.Boolean(), nullable=True, comment='是否为系统内置配置'),
        sa.Column('is_readonly', sa.Boolean(), nullable=True, comment='是否只读'),
        sa.Column('updated_by', sa.String(), nullable=True, comment='最后更新者ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('key')
    )
    
    # Create indexes
    op.create_index('ix_system_settings_category', 'system_settings', ['category'], unique=False)
    op.create_index('ix_system_settings_updated_at', 'system_settings', ['updated_at'], unique=False)
    
    # Insert default system settings
    op.execute("""
        INSERT INTO system_settings (key, value, value_type, category, description, default_value, is_system, is_readonly)
        VALUES 
        ('free_user_background_generation_limit', '3', 'INTEGER', 'SUBSCRIPTION_LIMITS', '免费用户每日背景图生成限制', '3', true, false),
        ('free_user_chat_total_limit', '100', 'INTEGER', 'SUBSCRIPTION_LIMITS', '免费用户总聊天次数限制', '100', true, false),
        ('free_user_agent_creation_limit', '6', 'INTEGER', 'SUBSCRIPTION_LIMITS', '免费用户Agent创建数量限制', '6', true, false);
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_system_settings_updated_at', table_name='system_settings')
    op.drop_index('ix_system_settings_category', table_name='system_settings')
    
    # Drop table
    op.drop_table('system_settings')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS settingtype')
    op.execute('DROP TYPE IF EXISTS settingcategory')