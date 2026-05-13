"""chat_history 表添加 deleted_at 软删除字段

Revision ID: 21b230fe0e6e
Revises: 2c1d10b2202b
Create Date: 2025-12-10 13:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21b230fe0e6e"
down_revision: Union[str, None] = "2c1d10b2202b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_history",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="软删除时间",
        ),
    )
    op.create_index(
        "ix_chat_history_deleted_at",
        "chat_history",
        ["deleted_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_chat_history_deleted_at", table_name="chat_history")
    op.drop_column("chat_history", "deleted_at")
