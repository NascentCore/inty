"""users add last_android_app_version_code

Used for feature gating in the push worker. Set when Android client calls
POST /api/v1/version/check.

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a7b9
Create Date: 2026-02-17 14:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c0"
down_revision: Union[str, None] = "c3d4e5f6a7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "last_android_app_version_code",
            sa.Integer(),
            nullable=True,
            comment="Last Android app version code reported by client on POST /api/v1/version/check; used for feature gating in the push worker. Android-specific because backend may serve iOS in the future.",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "last_android_app_version_code")
