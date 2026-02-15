"""add metadata column to memory

Revision ID: 9e4b5a6c7d8e
Revises: f055c1912687
Create Date: 2026-02-15 23:25:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e4b5a6c7d8e"
down_revision: Union[str, None] = "f055c1912687"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "memory",
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=True,
            comment=(
                "记忆扩展字段；节日记忆使用 {'festival_name': str, 'festival_data': 'YYYY-MM-DD'}"
            ),
        ),
    )
    # 迁移关键步骤：把历史 festival_name/festival_date 回填到 metadata，平滑兼容新读路径。
    op.execute(
        sa.text(
            """
            UPDATE memory
            SET metadata = json_build_object(
                'festival_name', festival_name,
                'festival_data', festival_date::text,
                'festival_date', festival_date::text
            )
            WHERE memory_type = 'festival'
                AND metadata IS NULL
                AND festival_name IS NOT NULL
                AND festival_date IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("memory", "metadata")
