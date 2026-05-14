"""Add content_mode to companion_memory_document_versions.

Revision ID: 20260514_memory_doc_content_mode
Revises: 20260512_phone_call_bindings
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260514_memory_doc_content_mode"
down_revision: Union[str, None] = "20260512_phone_call_bindings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companion_memory_document_versions",
        sa.Column(
            "content_mode",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'snapshot'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("companion_memory_document_versions", "content_mode")
