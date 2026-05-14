"""移除 users.is_active 冗余字段 CREATED_BY_AGENT

Revision ID: 6a8ac9b77c0c
Revises: 1055e2288eca
Create Date: 2025-11-27 21:05:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a8ac9b77c0c"
down_revision: Union[str, None] = "1055e2288eca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the redundant is_active column because deleted_at is authoritative."""
    op.drop_column("users", "is_active")


def downgrade() -> None:
    """Recreate the is_active column for backward compatibility."""
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=True,
            comment="账号是否激活",
        ),
    )
