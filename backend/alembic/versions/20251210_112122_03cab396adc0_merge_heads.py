"""merge heads

Revision ID: 03cab396adc0
Revises: 20251203_100347, 21b230fe0e6e
Create Date: 2025-12-10 11:21:22.005626+00:00

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "03cab396adc0"
down_revision: Union[str, None] = ("20251203_100347", "21b230fe0e6e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
