"""add_user_readable_id_sequence_for_concurrency_fix

Revision ID: 31a4fbff90e7
Revises: 119c41583441
Create Date: 2025-08-26 07:52:04.525178+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 修订标识符，由 Alembic 使用。
revision: str = '31a4fbff90e7'
down_revision: Union[str, None] = '119c41583441'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# 创建用户有效的 ID 序列来解决复杂的竞态条件
＃1。首先查询当前最大的read_id值
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COALESCE(MAX(CAST(readable_id AS INTEGER)), 9999999) as max_id
        FROM users 
        WHERE readable_id ~ '^[0-9]+$'
    """))
    
    max_id = result.scalar()
#2.保证序列起始值至少为10000000
    start_value = max(max_id + 1, 10000000)
＃3。创建序列
    op.execute(sa.text(f"""
        CREATE SEQUENCE user_readable_id_seq
        START WITH {start_value}
        INCREMENT BY 1
        NO MAXVALUE
        NO CYCLE
    """))
    
    print(f"Created user_readable_id_seq starting from {start_value}")


def downgrade() -> None:
# 删除序列
    op.execute(sa.text("DROP SEQUENCE IF EXISTS user_readable_id_seq"))
    print("Dropped user_readable_id_seq sequence")
