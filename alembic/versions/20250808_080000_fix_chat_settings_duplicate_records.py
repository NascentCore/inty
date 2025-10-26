"""Fix chat_settings duplicate records

Revision ID: 20250808_080000
Revises: 20250806_120000
Create Date: 2025-08-08 08:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '20250808_080000'
down_revision = ['20250806_120000', 'f7f85747dd24']
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix chat_settings duplicate records by cleaning duplicates and adding unique constraint"""
    
    # 检查并创建唯一约束（幂等操作）
    op.execute("""
        DO $$
        BEGIN
            -- 清理重复记录，保留每个chat_id的最新记录
            DELETE FROM chat_settings 
            WHERE id NOT IN (
                SELECT DISTINCT ON (chat_id) id
                FROM chat_settings 
                ORDER BY chat_id, created_at DESC
            );
            
            -- 创建唯一约束索引（如果不存在）
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'chat_settings' 
                AND indexname = 'uq_chat_settings_chat_id'
            ) THEN
                CREATE UNIQUE INDEX uq_chat_settings_chat_id 
                ON chat_settings (chat_id);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    """Remove unique constraint"""
    op.execute("""
        DROP INDEX IF EXISTS uq_chat_settings_chat_id;
    """)