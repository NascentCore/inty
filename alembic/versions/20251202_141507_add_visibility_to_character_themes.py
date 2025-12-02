"""add visibility to character themes

Revision ID: 20251202_141507
Revises: 20251201_154257
Create Date: 2025-12-02 14:15:07.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251202_141507"
down_revision: Union[str, None] = "20251201_154257"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for character_theme_visibility
    op.execute(
        "CREATE TYPE character_theme_visibility AS ENUM ('PRIMARY', 'SECONDARY', 'HIDDEN')"
    )

    # Add visibility column with default value
    op.add_column(
        "character_themes",
        sa.Column(
            "visibility",
            sa.Enum(
                "PRIMARY", "SECONDARY", "HIDDEN", name="character_theme_visibility"
            ),
            nullable=False,
            server_default="HIDDEN",
            comment="可见性：第一展示、第二展示、不可见",
        ),
    )

    # Create index on visibility column
    op.create_index(
        op.f("ix_character_themes_visibility"),
        "character_themes",
        ["visibility"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_character_themes_visibility"), table_name="character_themes")
    op.drop_column("character_themes", "visibility")
    op.execute("DROP TYPE character_theme_visibility")
