"""Add chat_id to messages table if not exists

Revision ID: 20250718_014000
Revises: 20250718_012500
Create Date: 2025-07-18 01:40:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250718_014000"
down_revision: Union[str, None] = "20250718_012500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if chat_id column exists, if not, add it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("messages")]

    if "chat_id" not in columns:
        # Add chat_id column to messages table
        op.add_column(
            "messages", sa.Column("chat_id", sa.String(), nullable=True)
        )

        # Add foreign key constraint
        op.create_foreign_key(
            "fk_messages_chat_id", "messages", "chats", ["chat_id"], ["id"]
        )


def downgrade() -> None:
    # Check if chat_id column exists before trying to drop it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("messages")]

    if "chat_id" in columns:
        # Drop foreign key constraint first
        op.drop_constraint(
            "fk_messages_chat_id", "messages", type_="foreignkey"
        )

        # Drop the column
        op.drop_column("messages", "chat_id")
