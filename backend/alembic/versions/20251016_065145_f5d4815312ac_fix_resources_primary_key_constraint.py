"""fix_resources_primary_key_constraint

Revision ID: f5d4815312ac
Revises: 355ceb5017ff
Create Date: 2025-10-16 06:51:45.358871+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5d4815312ac"
down_revision: Union[str, None] = "355ceb5017ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 检查 resources 表是否存在主键约束
    # 如果不存在，则添加 url 列作为主键
    connection = op.get_bind()

    # 检查是否已有主键约束
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.table_constraints 
        WHERE table_name = 'resources' 
        AND constraint_type = 'PRIMARY KEY'
    """))

    has_primary_key = result.scalar() > 0

    if not has_primary_key:
        # 确保 url 列不为空
        op.alter_column("resources", "url", nullable=False)

        # 添加主键约束
        op.create_primary_key("pk_resources", "resources", ["url"])

        # 确保有 url 列的索引
        result = connection.execute(sa.text("""
                    SELECT COUNT(*) 
                    FROM pg_indexes 
                    WHERE tablename = 'resources' 
                    AND indexname = 'ix_resources_url'
                """))
        index_exists = result.scalar() > 0

        if not index_exists:
            op.create_index("ix_resources_url", "resources", ["url"], unique=False)
    else:
        # 如果已有主键，检查是否是 url 列
        result = connection.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.key_column_usage 
            WHERE table_name = 'resources' 
            AND constraint_name IN (
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'resources' 
                AND constraint_type = 'PRIMARY KEY'
            )
        """))

        pk_columns = [row[0] for row in result.fetchall()]
        if "url" not in pk_columns:
            # 如果主键不是 url，需要先删除现有主键再添加新的
            # 获取实际的主键约束名称
            result = connection.execute(sa.text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'resources' 
                AND constraint_type = 'PRIMARY KEY'
            """))
            constraint_name = result.scalar()

            if constraint_name:
                op.drop_constraint(constraint_name, "resources", type_="primary")

            op.create_primary_key("pk_resources", "resources", ["url"])


def downgrade() -> None:
    # 删除主键约束
    op.drop_constraint("pk_resources", "resources", type_="primary")

    # 将 url 列改为可空
    op.alter_column("resources", "url", nullable=True)
