"""Rename companion_workspace_document_versions to companion_memory_document_versions.

Revision ID: 20260508_120000_rename_ws_docs
Revises: 20260418_120000_status_line
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260508_120000_rename_ws_docs"
down_revision: Union[str, None] = "20260418_120000_status_line"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_TABLE = "companion_workspace_document_versions"
_NEW_TABLE = "companion_memory_document_versions"
_OLD_INDEX = "ix_companion_ws_doc_scope_kind_date_seq"
_NEW_INDEX = "ix_companion_memory_doc_scope_kind_date_seq"


def upgrade() -> None:
    op.rename_table(_OLD_TABLE, _NEW_TABLE)
    op.execute(f'ALTER INDEX "{_OLD_INDEX}" RENAME TO "{_NEW_INDEX}"')


def downgrade() -> None:
    op.execute(f'ALTER INDEX "{_NEW_INDEX}" RENAME TO "{_OLD_INDEX}"')
    op.rename_table(_NEW_TABLE, _OLD_TABLE)
