"""add_quarterly_subscription_type

Revision ID: 20250703_130000
Revises: 20250703_120000
Create Date: 2025-07-03 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250703_130000"
down_revision: Union[str, None] = "20250703_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加QUARTERLY到现有的枚举类型
    op.execute("ALTER TYPE subscriptionplantype ADD VALUE 'QUARTERLY'")


def downgrade() -> None:
    # 注意：PostgreSQL不支持直接删除枚举值，需要重新创建枚举
    # 这里提供一个完整的回退方案

    # 1. 创建临时枚举
    op.execute("CREATE TYPE subscriptionplantype_temp AS ENUM ('MONTHLY', 'YEARLY')")

    # 2. 删除包含QUARTERLY的记录（如果有的话）
    op.execute("DELETE FROM subscription_plans WHERE plan_type = 'QUARTERLY'")

    # 3. 更新列类型
    op.execute(
        "ALTER TABLE subscription_plans ALTER COLUMN plan_type TYPE subscriptionplantype_temp USING plan_type::text::subscriptionplantype_temp"
    )

    # 4. 删除旧枚举
    op.execute("DROP TYPE subscriptionplantype")

    # 5. 重命名新枚举
    op.execute("ALTER TYPE subscriptionplantype_temp RENAME TO subscriptionplantype")
