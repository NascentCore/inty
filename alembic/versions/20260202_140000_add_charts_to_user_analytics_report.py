"""add charts column to user_analytics_report

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-02-02 14:00:00.000000+00:00

CREATED_BY_AGENT
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_analytics_report",
        sa.Column(
            "charts",
            JSONB,
            nullable=True,
            comment="图表数据：new_users, conversation_rounds, user_rounds_distribution, users_hitting_limit, popular_agents",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_analytics_report", "charts")
