"""modify push_notification_history table

Revision ID: 20251113_180000
Revises: 20251111_140711
Create Date: 2025-11-13 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251113_180000"
down_revision: Union[str, None] = "20251111_140711"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除旧的唯一约束
    op.drop_index(
        "uq_push_notification_chat_stage",
        table_name="push_notification_history",
    )

    # 2. 修改 chat_id 为可空
    op.alter_column(
        "push_notification_history",
        "chat_id",
        existing_type=sa.String(),
        nullable=True,
        existing_nullable=False,
    )

    # 3. 添加 push_type 字段
    op.add_column(
        "push_notification_history",
        sa.Column(
            "push_type",
            sa.String(),
            nullable=False,
            server_default="recent_chat",
            comment="推送类型: no_chat（无聊天推送）, recent_chat（最近聊天推送）",
        ),
    )

    # 4. 更新现有记录的 push_type
    op.execute(
        "UPDATE push_notification_history SET push_type = 'recent_chat' WHERE push_type = 'recent_chat'"
    )

    # 5. 修改 stage 字段的注释
    op.alter_column(
        "push_notification_history",
        "stage",
        existing_type=sa.String(),
        existing_nullable=False,
        comment="推送阶段: 10min, 30min, 2h, no_chat_24h, no_chat_48h 等",
    )

    # 6. 创建新的唯一约束（支持有 chat_id 和无 chat_id 两种情况）
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

    # 7. 添加 push_type 索引
    op.create_index(
        "ix_push_notification_push_type",
        "push_notification_history",
        ["push_type"],
        unique=False,
    )


def downgrade() -> None:
    # 删除新索引
    op.drop_index(
        "ix_push_notification_push_type", table_name="push_notification_history"
    )
    op.drop_index(
        "uq_push_notification_user_stage_no_chat",
        table_name="push_notification_history",
    )
    op.drop_index(
        "uq_push_notification_chat_stage",
        table_name="push_notification_history",
    )

    # 删除 push_type 字段
    op.drop_column("push_notification_history", "push_type")

    # 恢复 chat_id 为不可空（需要先清理 NULL 值）
    op.execute("DELETE FROM push_notification_history WHERE chat_id IS NULL")
    op.alter_column(
        "push_notification_history",
        "chat_id",
        existing_type=sa.String(),
        nullable=False,
        existing_nullable=True,
    )

    # 恢复旧的唯一约束
    op.create_index(
        "uq_push_notification_chat_stage",
        "push_notification_history",
        ["chat_id", "stage"],
        unique=True,
    )
