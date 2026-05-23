"""Add voice features: voice_cache table for voice caching

Revision ID: 20250715_140000
Revises: 20250715_084500
Create Date: 2025-07-15 14:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250715_140000"
down_revision: Union[str, None] = "20250715_084500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create voice_cache table (no changes to chat_settings as voice_enabled already exists)
    op.create_table(
        "voice_cache",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("voice_id", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("audio_url", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True, default=0),
        sa.Column("hit_count", sa.Integer(), nullable=True, default=0),
        sa.Column(
            "last_accessed",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash"),
    )

    # Create indexes for voice_cache table
    op.create_index(
        "ix_voice_cache_content_hash", "voice_cache", ["content_hash"]
    )
    op.create_index("ix_voice_cache_id", "voice_cache", ["id"])


def downgrade() -> None:
    # Drop voice_cache table
    op.drop_index("ix_voice_cache_id", table_name="voice_cache")
    op.drop_index("ix_voice_cache_content_hash", table_name="voice_cache")
    op.drop_table("voice_cache")
