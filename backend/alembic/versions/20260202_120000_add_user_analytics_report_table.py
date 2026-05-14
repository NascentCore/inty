"""add user_analytics_report table

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-02-02 12:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_analytics_report",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "report_type",
            sa.String(16),
            nullable=False,
            comment="daily | weekly",
        ),
        sa.Column(
            "report_date",
            sa.Date(),
            nullable=False,
            comment="日报：统计日期；周报：该周周一日期",
        ),
        sa.Column(
            "stats",
            JSONB,
            nullable=False,
            comment="UserAnalyticsStatsResponse 的完整 JSON",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_user_analytics_report_type_date",
        "user_analytics_report",
        ["report_type", "report_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_analytics_report_type_date",
        table_name="user_analytics_report",
    )
    op.drop_table("user_analytics_report")
