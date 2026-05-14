"""add exclusive_photos to agents

Revision ID: d1e2f3a4b5c6
Revises: cbde9132ac88
Create Date: 2026-02-11 18:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "cbde9132ac88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "exclusive_photos",
            sa.JSON(),
            nullable=True,
            comment="运营上传的专属角色照：每项含 image_url, caption, credits_required",
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "exclusive_photos")
