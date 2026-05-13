"""add report_type to report table

Revision ID: 20251124_193339
Revises: 20251114_142810
Create Date: 2025-11-24 19:33:39.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251124_193339"
down_revision: Union[str, None] = "20251114_142810"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建枚举类型
    reporttype = postgresql.ENUM("REPORT", "FEEDBACK", name="reporttype")
    reporttype.create(op.get_bind(), checkfirst=True)
    # 添加 report_type 字段，允许为空，为空时业务逻辑中视为 REPORT
    op.add_column(
        "report",
        sa.Column(
            "report_type",
            sa.Enum("REPORT", "FEEDBACK", name="reporttype"),
            nullable=True,
            comment="记录类型：举报或反馈，为空时默认为 REPORT",
        ),
    )


def downgrade() -> None:
    # 移除 report_type 字段
    op.drop_column("report", "report_type")
    # 删除枚举类型
    reporttype = postgresql.ENUM("REPORT", "FEEDBACK", name="reporttype")
    reporttype.drop(op.get_bind(), checkfirst=True)
