"""merge_chat_and_report_migrations

Revision ID: 24a617b81c38
Revises: f2d17f26e79d, f7156cf8bdcf
Create Date: 2025-06-05 11:46:27.642783+00:00

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '24a617b81c38'
down_revision: Union[str, None] = ('f2d17f26e79d', 'f7156cf8bdcf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
