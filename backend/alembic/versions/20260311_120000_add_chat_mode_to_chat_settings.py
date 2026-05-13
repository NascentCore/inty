"""add chat_mode to chat_settings

Revision ID: 20260311_120000
Revises: 6f8c4a2d9b11
Create Date: 2026-03-11 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260311_120000"
down_revision: Union[str, None] = "6f8c4a2d9b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [column["name"] for column in inspector.get_columns("chat_settings")]

    if "chat_mode" not in columns:
        op.add_column(
            "chat_settings",
            sa.Column(
                "chat_mode",
                sa.String(),
                nullable=True,
                comment="User-selected chat mode id (e.g. flirting_mode_20250902). Null = use agent default.",
            ),
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [column["name"] for column in inspector.get_columns("chat_settings")]

    if "chat_mode" in columns:
        op.drop_column("chat_settings", "chat_mode")
