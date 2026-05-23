"""migrate_chat_history_to_alembic_with_audio_url

Revision ID: 75796d073cb2
Revises: 31a4fbff90e7
Create Date: 2025-09-09 02:47:19.386052+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "75796d073cb2"
down_revision: Union[str, None] = "31a4fbff90e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table exists and handle accordingly
    connection = op.get_bind()

    # Check if chat_history table exists
    table_exists = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'chat_history')"
        )
    ).scalar()

    if table_exists:
        # Table exists (created by langchain_postgres), add audio_url column
        op.add_column(
            "chat_history", sa.Column("audio_url", sa.String(), nullable=True)
        )

        # Check if index exists before creating it
        index_exists = connection.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE tablename = 'chat_history' AND indexname = 'idx_chat_history_session_id'
            )
            """)).scalar()

        if not index_exists:
            op.create_index(
                "idx_chat_history_session_id", "chat_history", ["session_id"]
            )
    else:
        # Table doesn't exist, create it with all columns including audio_url
        op.create_table(
            "chat_history",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "session_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column(
                "message",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
            ),
            sa.Column("audio_url", sa.String(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_chat_history_session_id", "chat_history", ["session_id"]
        )


def downgrade() -> None:
    # Only remove the audio_url column, don't drop the entire table
    # since it might have been created by langchain_postgres
    connection = op.get_bind()

    # Check if audio_url column exists
    column_exists = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'chat_history' AND column_name = 'audio_url'
        )
        """)).scalar()

    if column_exists:
        op.drop_column("chat_history", "audio_url")
