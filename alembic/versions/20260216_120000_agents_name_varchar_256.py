"""agents.name 列长度由 VARCHAR(30) 扩展为 VARCHAR(256)

Revision ID: b2c3d4e5f6a8
Revises: 9e4b5a6c7d8e
Create Date: 2026-02-16 12:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, None] = "9e4b5a6c7d8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "agents",
        "name",
        existing_type=sa.String(30),
        type_=sa.String(256),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "agents",
        "name",
        existing_type=sa.String(256),
        type_=sa.String(30),
        existing_nullable=False,
    )
