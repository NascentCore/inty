"""Add premium_mode to chat_settings

Revision ID: 20250806_120000
Revises: a1935acfeee0
Create Date: 2025-08-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250806_120000'
down_revision = 'a1935acfeee0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add premium_mode column to chat_settings table"""
    # Check if the column already exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('chat_settings')]
    
    if 'premium_mode' not in columns:
        # Add column as nullable first
        op.add_column('chat_settings', sa.Column('premium_mode', sa.Boolean(), nullable=True, comment='高级模式开关，仅订阅用户可设置'))
        
        # Update existing rows to set default value
        connection.execute(sa.text("UPDATE chat_settings SET premium_mode = false WHERE premium_mode IS NULL"))
        
        # Make the column non-nullable
        op.alter_column('chat_settings', 'premium_mode', nullable=False)


def downgrade() -> None:
    """Remove premium_mode column from chat_settings table"""
    # Check if the column exists before trying to drop it
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('chat_settings')]
    
    if 'premium_mode' in columns:
        op.drop_column('chat_settings', 'premium_mode')