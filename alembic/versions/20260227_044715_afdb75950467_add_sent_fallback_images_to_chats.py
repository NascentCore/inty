"""add_sent_fallback_images_to_chats

Revision ID: afdb75950467
Revises: e5f6a7b8c9d1
Create Date: 2026-02-27 04:47:15.853282+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'afdb75950467'
down_revision: Union[str, None] = 'e5f6a7b8c9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chats",
        sa.Column(
            "sent_fallback_images",
            sa.JSON(),
            nullable=True,
            comment="当前 chat 已发送过的兜底图片 image_id 列表（用于去重）",
        ),
    )


def downgrade() -> None:
    op.drop_column("chats", "sent_fallback_images")
