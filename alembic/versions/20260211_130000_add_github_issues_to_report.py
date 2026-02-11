"""add github_issues to report table

Revision ID: d1a2b3c4d5e6
Revises: c0d9e8f7a6b5
Create Date: 2026-02-11 13:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1a2b3c4d5e6"
down_revision: Union[str, None] = "c0d9e8f7a6b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report",
        sa.Column(
            "github_issues",
            sa.String(length=500),
            nullable=True,
            comment="关联的 GitHub issue URL",
        ),
    )


def downgrade() -> None:
    op.drop_column("report", "github_issues")
