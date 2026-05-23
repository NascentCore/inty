"""create device_tokens table

Revision ID: 3a4b5a59c152
Revises: 65cecc256473
Create Date: 2025-06-11 05:42:13.053877+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3a4b5a59c152"
down_revision: Union[str, None] = "65cecc256473"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("token", sa.Text, nullable=False, unique=True),
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
        sa.Index("ix_device_tokens_user_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("device_tokens")
