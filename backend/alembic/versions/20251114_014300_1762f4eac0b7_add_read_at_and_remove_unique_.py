"""add_read_at_and_remove_unique_constraints

Revision ID: 1762f4eac0b7
Revises: 20251113_180000
Create Date: 2025-11-14 01:43:00.552548+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1762f4eac0b7"
down_revision: Union[str, None] = "20251113_180000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除唯一约束索引
    op.drop_index(
        "uq_push_notification_chat_stage", table_name="push_notification_history"
    )
    op.drop_index(
        "uq_push_notification_user_stage_no_chat",
        table_name="push_notification_history",
    )

    # 2. 添加 read_at 字段
    op.add_column(
        "push_notification_history",
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="已读时间（用户发送新消息时标记为已读）",
        ),
    )

    # 3. 添加 read_at 索引
    op.create_index(
        "ix_push_notification_read_at",
        "push_notification_history",
        ["read_at"],
        unique=False,
    )

    # 4. 添加复合索引：用于查询未读推送（有 chat_id）
    op.create_index(
        "ix_push_notification_chat_stage_unread",
        "push_notification_history",
        ["chat_id", "stage", "read_at"],
        unique=False,
        postgresql_where=sa.text("read_at IS NULL AND chat_id IS NOT NULL"),
    )

    # 5. 添加复合索引：用于查询未读推送（无 chat_id）
    op.create_index(
        "ix_push_notification_user_stage_unread",
        "push_notification_history",
        ["user_id", "stage", "read_at"],
        unique=False,
        postgresql_where=sa.text("read_at IS NULL AND chat_id IS NULL"),
    )


def downgrade() -> None:
    # 删除新索引
    op.drop_index(
        "ix_push_notification_user_stage_unread", table_name="push_notification_history"
    )
    op.drop_index(
        "ix_push_notification_chat_stage_unread", table_name="push_notification_history"
    )
    op.drop_index(
        "ix_push_notification_read_at", table_name="push_notification_history"
    )

    # 删除 read_at 字段
    op.drop_column("push_notification_history", "read_at")

    # 恢复唯一约束索引
    op.create_index(
        "uq_push_notification_chat_stage",
        "push_notification_history",
        ["chat_id", "stage"],
        unique=True,
        postgresql_where=sa.text("chat_id IS NOT NULL"),
    )

    op.create_index(
        "uq_push_notification_user_stage_no_chat",
        "push_notification_history",
        ["user_id", "stage"],
        unique=True,
        postgresql_where=sa.text("chat_id IS NULL"),
    )
