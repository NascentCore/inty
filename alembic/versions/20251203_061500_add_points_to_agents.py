"""add points column to agents

Revision ID: 20251203_061500
Revises: 20251202_141507
Create Date: 2025-12-03 06:15:00.000000

"""

# CREATED_BY_AGENT

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251203_061500"
down_revision: Union[str, None] = "20251202_141507"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "points",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Boost points used for explore boosting feature",
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "points")
