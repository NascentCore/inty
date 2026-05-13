"""Add style_prompt to chat_settings

Revision ID: 20250804_150000
Revises: 20250804_120000
Create Date: 2025-08-04 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250804_150000'
down_revision = '20250804_120000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add style_prompt column to chat_settings table"""
    # Check if the column already exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('chat_settings')]
    
    if 'style_prompt' not in columns:
        op.add_column('chat_settings', sa.Column('style_prompt', sa.Text(), nullable=True, comment='风格提示词，仅订阅用户可设置'))


def downgrade() -> None:
    """Remove style_prompt column from chat_settings table"""
    # Check if the column exists before trying to drop it
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('chat_settings')]
    
    if 'style_prompt' in columns:
        op.drop_column('chat_settings', 'style_prompt')