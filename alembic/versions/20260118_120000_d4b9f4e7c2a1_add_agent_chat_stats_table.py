"""Add agent_chat_stats table.

Revision ID: d4b9f4e7c2a1
Revises: 83f37ed3d576
Create Date: 2026-01-18 12:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b9f4e7c2a1"
down_revision: Union[str, None] = "83f37ed3d576"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_chat_stats",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("messages_count", sa.Integer(), nullable=False),
        sa.Column("users_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id", "period"),
    )


def downgrade() -> None:
    op.drop_table("agent_chat_stats")
