"""add chat background image to chat_settings

Revision ID: 20251126_120000
Revises: 338a576cd178
Create Date: 2025-11-26 12:00:00.000000

"""

# CREATED_BY_AGENT

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251126_120000"
down_revision: Union[str, None] = "338a576cd178"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_settings",
        sa.Column(
            "background_image",
            sa.JSON(),
            nullable=True,
            comment="用户为该聊天选择的背景图（存储生成图片元数据）",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_settings", "background_image")

