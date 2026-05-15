"""Bridge migration from v1.0.1-dev to main

Revision ID: f7f85747dd24
Revises: 43b18ddc9846
Create Date: 2025-08-08 07:31:25.068007+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f7f85747dd24'
down_revision = '43b18ddc9846'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Bridge upgrade - checks if unique constraint exists before creating"""
    
    # 检查唯一索引是否已存在，如果不存在则创建
    # 这样可以安全地从v1.0.1-dev迁移到main
    op.execute("""
        DO $$
        BEGIN
            -- 清理重复的 chat_settings 数据（如果有）
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
    op.execute("DROP INDEX IF EXISTS uq_chat_settings_chat_id;")