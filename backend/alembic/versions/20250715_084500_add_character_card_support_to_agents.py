"""Add character card support to agents

Revision ID: 20250715_084500
Revises: 00e81036d2ba
Create Date: 2025-07-15 08:45:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250715_084500"
down_revision: Union[str, None] = "00e81036d2ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add character card related columns to agents table
    op.add_column(
        "agents", sa.Column("character_card_spec", sa.String(), nullable=True)
    )
    op.add_column(
        "agents", sa.Column("character_card_data", sa.JSON(), nullable=True)
    )
    op.add_column("agents", sa.Column("personality", sa.Text(), nullable=True))
    op.add_column("agents", sa.Column("scenario", sa.Text(), nullable=True))
    op.add_column(
        "agents", sa.Column("first_message", sa.Text(), nullable=True)
    )
    op.add_column(
        "agents", sa.Column("message_example", sa.Text(), nullable=True)
    )
    op.add_column(
        "agents", sa.Column("creator_notes", sa.Text(), nullable=True)
    )
    op.add_column(
        "agents",
        sa.Column("post_history_instructions", sa.Text(), nullable=True),
    )
    op.add_column(
        "agents", sa.Column("alternate_greetings", sa.JSON(), nullable=True)
    )
    op.add_column(
        "agents", sa.Column("character_book", sa.JSON(), nullable=True)
    )
    op.add_column("agents", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column(
        "agents", sa.Column("character_version", sa.String(), nullable=True)
    )
    op.add_column("agents", sa.Column("extensions", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove character card related columns from agents table
    op.drop_column("agents", "extensions")
    op.drop_column("agents", "character_version")
    op.drop_column("agents", "tags")
    op.drop_column("agents", "character_book")
    op.drop_column("agents", "alternate_greetings")
    op.drop_column("agents", "post_history_instructions")
    op.drop_column("agents", "creator_notes")
    op.drop_column("agents", "message_example")
    op.drop_column("agents", "first_message")
    op.drop_column("agents", "scenario")
    op.drop_column("agents", "personality")
    op.drop_column("agents", "character_card_data")
    op.drop_column("agents", "character_card_spec")
