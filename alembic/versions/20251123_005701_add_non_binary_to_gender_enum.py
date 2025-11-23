"""add NON_BINARY to gender enum

Revision ID: 20251123_005701
Revises: 0123b2d0bf3c
Create Date: 2025-11-23 00:57:01.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251123_005701"
down_revision = "0123b2d0bf3c"
branch_labels = None
depends_on = None


def upgrade():
    # 在 PostgreSQL 中为 gender 枚举类型添加 NON_BINARY 值
    # 使用 DO 块来检查值是否已存在，避免重复添加
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'NON_BINARY' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'gender')
            ) THEN
                ALTER TYPE gender ADD VALUE 'NON_BINARY';
            END IF;
        END $$;
    """)


def downgrade():
    # PostgreSQL 不支持直接删除枚举值
    # 如果需要回滚，需要重新创建枚举类型并迁移数据
    # 这是一个破坏性操作，需要：
    # 1. 将使用 NON_BINARY 的记录更新为其他值（如 OTHER）
    # 2. 创建新的枚举类型（不包含 NON_BINARY）
    # 3. 更新列类型
    # 4. 删除旧枚举类型
    # 
    # 由于操作复杂且可能丢失数据，这里只提供注释说明
    # 实际回滚需要根据业务需求谨慎处理
    pass

