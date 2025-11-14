"""add version column to agents

Revision ID: 20251114_090000
Revises: 20251113_180000
Create Date: 2025-11-14 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251114_090000"
down_revision: Union[str, None] = "20251113_180000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="记录变更版本号，每次更新自动递增",
        ),
    )
    op.execute("UPDATE agents SET version = COALESCE(version, 1)")


def downgrade() -> None:
    op.drop_column("agents", "version")
