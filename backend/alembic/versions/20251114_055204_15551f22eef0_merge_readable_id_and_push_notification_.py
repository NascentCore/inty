"""merge readable_id and push_notification branches

Revision ID: 15551f22eef0
Revises: 4a90b1f01430, 1762f4eac0b7
Create Date: 2025-11-14 05:52:04.615316+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15551f22eef0'
down_revision: Union[str, None] = ('4a90b1f01430', '1762f4eac0b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
