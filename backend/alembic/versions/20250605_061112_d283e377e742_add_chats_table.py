"""add_chats_table

Revision ID: d283e377e742
Revises: 959ca996a9d7
Create Date: 2025-06-05 06:11:12.721854+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d283e377e742"
down_revision: Union[str, None] = "959ca996a9d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 chats 表
    op.create_table(
        "chats",
        sa.Column("id", sa.VARCHAR(), nullable=False),
        sa.Column("user_id", sa.VARCHAR(), nullable=False),
        sa.Column("agent_id", sa.VARCHAR(), nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), nullable=True, default=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chats_id", "chats", ["id"], unique=False)


def downgrade() -> None:
    # 删除 chats 表
    op.drop_index("ix_chats_id", table_name="chats")
    op.drop_table("chats")
