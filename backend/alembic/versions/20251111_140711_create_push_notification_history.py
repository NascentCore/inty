"""create push_notification_history table

Revision ID: 20251111_140711
Revises: 20250130_120000
Create Date: 2025-11-11 14:07:11.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251111_140711"
down_revision: Union[str, None] = "20250130_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_notification_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("chat_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column(
            "stage",
            sa.String(),
            nullable=False,
            comment="推送阶段: 10min, 30min, 2h",
        ),
        sa.Column(
            "message_content",
            sa.Text(),
            nullable=True,
            comment="生成的Agent消息内容",
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="发送时间",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["chats.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_push_notification_history_id",
        "push_notification_history",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_push_notification_history_chat_id",
        "push_notification_history",
        ["chat_id"],
        unique=False,
    )
    op.create_index(
        "ix_push_notification_history_user_id",
        "push_notification_history",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_push_notification_history_agent_id",
        "push_notification_history",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_push_notification_history_sent_at",
        "push_notification_history",
        ["sent_at"],
        unique=False,
    )
    op.create_index(
        "uq_push_notification_chat_stage",
        "push_notification_history",
        ["chat_id", "stage"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_push_notification_chat_stage",
        table_name="push_notification_history",
    )
    op.drop_index(
        "ix_push_notification_history_sent_at",
        table_name="push_notification_history",
    )
    op.drop_index(
        "ix_push_notification_history_agent_id",
        table_name="push_notification_history",
    )
    op.drop_index(
        "ix_push_notification_history_user_id",
        table_name="push_notification_history",
    )
    op.drop_index(
        "ix_push_notification_history_chat_id",
        table_name="push_notification_history",
    )
    op.drop_index(
        "ix_push_notification_history_id",
        table_name="push_notification_history",
    )
    op.drop_table("push_notification_history")
