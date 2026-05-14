"""add debug_messages field to chats table

Revision ID: 00e81036d2ba
Revises: a1b2c3d4e5f6
Create Date: 2025-07-14 10:28:46.544113+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = "00e81036d2ba"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 debug_messages 字段到 chats 表
    op.add_column(
        "chats",
        sa.Column(
            "debug_messages",
            JSON,
            nullable=True,
            comment="最新一次发送给大模型的完整messages列表（JSON格式）",
        ),
    )


def downgrade() -> None:
    # 删除 debug_messages 字段
    op.drop_column("chats", "debug_messages")
