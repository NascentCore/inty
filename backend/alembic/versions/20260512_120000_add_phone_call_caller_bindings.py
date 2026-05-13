"""Add phone-call caller bindings.

Revision ID: 20260512_phone_call_bindings
Revises: 20260508_120000_rename_ws_docs
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260512_phone_call_bindings"
down_revision: Union[str, None] = "20260508_120000_rename_ws_docs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "phone_call_caller_bindings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("phone_number_hmac", sa.String(length=64), nullable=False),
        sa.Column("phone_number_masked", sa.String(length=32), nullable=False),
        sa.Column("last_agent_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["last_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number_hmac"),
    )
    op.create_index(
        "ix_phone_call_caller_bindings_phone_hmac",
        "phone_call_caller_bindings",
        ["phone_number_hmac"],
        unique=False,
    )
    op.create_index(
        "ix_phone_call_caller_bindings_user_id",
        "phone_call_caller_bindings",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_phone_call_caller_bindings_user_id",
        table_name="phone_call_caller_bindings",
    )
    op.drop_index(
        "ix_phone_call_caller_bindings_phone_hmac",
        table_name="phone_call_caller_bindings",
    )
    op.drop_table("phone_call_caller_bindings")
