"""remove_target_reporter_unique_constraint_from_report

Revision ID: 74d194ee0ff9
Revises: 20250625_154455
Create Date: 2025-07-01 03:11:17.534197+00:00

"""
from typing import Sequence, Union

from alembic import op
# 修订标识符，由 Alembic 使用。
revision: str = '74d194ee0ff9'
down_revision: Union[str, None] = '20250625_154455'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# 删除report表的target_id和reporter_id的唯一性约束
    op.drop_index('ix_report_target_reporter', table_name='report')


def downgrade() -> None:
# 重新创建报告表的 target_id 和 reports_id 的唯一联合性约束
    op.create_index('ix_report_target_reporter', 'report', ['target_id', 'reporter_id'], unique=True)
