"""Add agents.status_line for chat header mood tagline."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260418_120000_status_line"
down_revision: Union[str, None] = "512401673084"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "status_line",
            sa.String(),
            nullable=True,
            comment="Short mood/tagline for chat header; updated by companion tools",
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "status_line")
