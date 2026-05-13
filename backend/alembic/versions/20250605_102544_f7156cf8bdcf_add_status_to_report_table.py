"""add status to report table

Revision ID: f7156cf8bdcf
Revises: a893fe42f1cf
Create Date: 2025-06-05 10:25:44.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f7156cf8bdcf'
down_revision: Union[str, None] = 'a893fe42f1cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建枚举类型
    reportstatus = postgresql.ENUM('PENDING', 'PROCESSING', 'RESOLVED', 'REJECTED', name='reportstatus')
    reportstatus.create(op.get_bind(), checkfirst=True)
    # 增加status字段
    op.add_column('report', sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'RESOLVED', 'REJECTED', name='reportstatus'), nullable=False, server_default='PENDING', comment='举报处理状态'))


def downgrade() -> None:
    op.drop_column('report', 'status')
    # 删除枚举类型
    reportstatus = postgresql.ENUM('PENDING', 'PROCESSING', 'RESOLVED', 'REJECTED', name='reportstatus')
    reportstatus.drop(op.get_bind(), checkfirst=True)
