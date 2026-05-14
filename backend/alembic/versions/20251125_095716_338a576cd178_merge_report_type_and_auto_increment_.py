"""merge report_type and auto_increment_version branches

Revision ID: 338a576cd178
Revises: 0123b2d0bf3c, 20251124_193339
Create Date: 2025-11-25 09:57:16.414690+00:00

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "338a576cd178"
down_revision: Union[str, None] = ("0123b2d0bf3c", "20251124_193339")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
