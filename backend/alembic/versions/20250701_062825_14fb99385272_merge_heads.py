"""merge_heads

Revision ID: 14fb99385272
Revises: 20250129_120000, 74d194ee0ff9
Create Date: 2025-07-01 06:28:25.540473+00:00

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "14fb99385272"
down_revision: Union[str, None] = ("20250129_120000", "74d194ee0ff9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
