"""add voice_id to chat_settings

Revision ID: 6f8c4a2d9b11
Revises: 2449ffd5ff0c
Create Date: 2026-03-05 12:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f8c4a2d9b11"
down_revision: Union[str, None] = "2449ffd5ff0c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [
        column["name"] for column in inspector.get_columns("chat_settings")
    ]

    if "voice_id" not in columns:
        op.add_column(
            "chat_settings",
            sa.Column(
                "voice_id",
                sa.String(),
                nullable=True,
                comment="Per-chat selected voice id (MVP supports Gemini voices only)",
            ),
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [
        column["name"] for column in inspector.get_columns("chat_settings")
    ]

    if "voice_id" in columns:
        op.drop_column("chat_settings", "voice_id")
