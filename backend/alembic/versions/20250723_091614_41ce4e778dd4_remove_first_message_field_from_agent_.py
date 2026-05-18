"""Remove first_message field from Agent model

Revision ID: 41ce4e778dd4
Revises: df2112660694
Create Date: 2025-07-23 09:16:14.453502+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41ce4e778dd4'
down_revision: Union[str, None] = 'df2112660694'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove first_message column from agents table
    op.drop_column('agents', 'first_message')


def downgrade() -> None:
    # Add back first_message column to agents table
    op.add_column('agents', sa.Column('first_message', sa.Text(), nullable=True))
