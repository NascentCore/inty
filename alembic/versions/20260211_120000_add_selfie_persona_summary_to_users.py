"""add selfie_persona_summary to users

Revision ID: c4d5e6f7a8b9
Revises: b9c8d7e6f5a4
Create Date: 2026-02-11 12:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b9c8d7e6f5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "selfie_persona_summary",
            sa.String(length=255),
            nullable=True,
            comment="根据用户自拍推测的简短画像结论，用于聊天提示词",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "selfie_persona_summary")
