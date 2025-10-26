"""合并多个迁移分支

Revision ID: 474e96b4de1b
Revises: 3a4b5a59c152, 8f7a7e953b2c
Create Date: 2025-06-18 02:21:27.945813+00:00

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '474e96b4de1b'
down_revision: Union[str, None] = ('3a4b5a59c152', '8f7a7e953b2c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
