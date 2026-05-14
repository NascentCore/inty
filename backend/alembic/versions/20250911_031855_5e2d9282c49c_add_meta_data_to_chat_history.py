"""add_meta_data_to_chat_history

Revision ID: 5e2d9282c49c
Revises: ab7f71ad458d
Create Date: 2025-09-11 03:18:55.978813+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5e2d9282c49c"
down_revision: Union[str, None] = "ab7f71ad458d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add meta_data column to chat_history table
    op.add_column(
        "chat_history",
        sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    # Remove meta_data column from chat_history table
    op.drop_column("chat_history", "meta_data")
