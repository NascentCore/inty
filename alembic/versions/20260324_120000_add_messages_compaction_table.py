"""add messages_compaction table

Revision ID: 20260324_120000
Revises: 20260311_120000
Create Date: 2026-03-24 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260324_120000"
down_revision: Union[str, None] = "20260311_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = inspector.get_table_names()

    if "messages_compaction" not in table_names:
        op.create_table(
            "messages_compaction",
            sa.Column("key", sa.String(length=255), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("agent_id", sa.String(), nullable=False),
            sa.Column(
                "compacted_payload",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("key"),
        )
        op.create_index(
            "ix_messages_compaction_user_agent",
            "messages_compaction",
            ["user_id", "agent_id"],
            unique=False,
        )
        op.create_index(
            "ix_messages_compaction_user_id",
            "messages_compaction",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            "ix_messages_compaction_agent_id",
            "messages_compaction",
            ["agent_id"],
            unique=False,
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = inspector.get_table_names()
    if "messages_compaction" in table_names:
        op.drop_index(
            "ix_messages_compaction_agent_id",
            table_name="messages_compaction",
        )
        op.drop_index(
            "ix_messages_compaction_user_id",
            table_name="messages_compaction",
        )
        op.drop_index(
            "ix_messages_compaction_user_agent",
            table_name="messages_compaction",
        )
        op.drop_table("messages_compaction")
