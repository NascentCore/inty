"""add duration_seconds prompt_tokens completion_tokens to memory_extraction_log

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-01-27 14:00:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "memory_extraction_log",
        sa.Column(
            "duration_seconds", sa.Float(), nullable=True, comment="当次抽取总耗时秒"
        ),
    )
    op.add_column(
        "memory_extraction_log",
        sa.Column(
            "prompt_tokens", sa.Integer(), nullable=True, comment="LLM 输入 token 数"
        ),
    )
    op.add_column(
        "memory_extraction_log",
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=True,
            comment="LLM 输出 token 数",
        ),
    )


def downgrade() -> None:
    op.drop_column("memory_extraction_log", "completion_tokens")
    op.drop_column("memory_extraction_log", "prompt_tokens")
    op.drop_column("memory_extraction_log", "duration_seconds")
