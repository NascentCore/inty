"""remove_target_reporter_unique_constraint_from_report

Revision ID: 74d194ee0ff9
Revises: 20250625_154455
Create Date: 2025-07-01 03:11:17.534197+00:00

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "74d194ee0ff9"
down_revision: Union[str, None] = "20250625_154455"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 移除 report 表的 target_id 和 reporter_id 的联合唯一性约束
    op.drop_index("ix_report_target_reporter", table_name="report")


def downgrade() -> None:
    # 重新创建 report 表的 target_id 和 reporter_id 的联合唯一性约束
    op.create_index(
        "ix_report_target_reporter", "report", ["target_id", "reporter_id"], unique=True
    )
