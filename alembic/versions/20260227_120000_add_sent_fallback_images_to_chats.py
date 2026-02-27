"""add sent_fallback_images to chats

Revision ID: a1b2c3d4e5f6
Revises: e5f6a7b8c9d1
Create Date: 2026-02-27 12:00:00.000000+00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e5f6a7b8c9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chats",
        sa.Column(
            "sent_fallback_images",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="已展示的兜底图片 image_id 列表，用于排除后续兜底候选",
        ),
    )


def downgrade() -> None:
    op.drop_column("chats", "sent_fallback_images")
