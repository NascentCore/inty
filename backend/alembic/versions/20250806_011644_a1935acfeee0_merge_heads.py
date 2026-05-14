"""merge heads

Revision ID: a1935acfeee0
Revises: 20250804_150000, 43b18ddc9846
Create Date: 2025-08-06 01:16:44.935017+00:00

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "a1935acfeee0"
down_revision: Union[str, None] = ("20250804_150000", "43b18ddc9846")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
