"""Add main_prompt and mode_prompt fields to Agent model

Revision ID: df2112660694
Revises: 20250718_014000
Create Date: 2025-07-23 08:35:29.789603+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "df2112660694"
down_revision: Union[str, None] = "20250718_014000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add main_prompt column to agents table
    op.add_column("agents", sa.Column("main_prompt", sa.Text(), nullable=True))

    # Add mode_prompt column to agents table
    op.add_column("agents", sa.Column("mode_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove mode_prompt column from agents table
    op.drop_column("agents", "mode_prompt")

    # Remove main_prompt column from agents table
    op.drop_column("agents", "main_prompt")
