"""Add user deletion fields and audit table

Revision ID: 20250718_012500
Revises: 20250715_140000
Create Date: 2025-07-18 01:25:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250718_012500"
down_revision: Union[str, None] = "20250715_140000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add deletion fields to users table
    op.add_column(
        "users",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="账户删除时间",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "anonymized_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="数据匿名化时间",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "deletion_reason", sa.String(255), nullable=True, comment="删除原因"
        ),
    )

    # Create user deletion audit table
    op.create_table(
        "user_deletion_logs",
        sa.Column("id", sa.String(), primary_key=True, comment="删除日志ID"),
        sa.Column(
            "user_id", sa.String(), nullable=False, comment="被删除的用户ID"
        ),
        sa.Column(
            "original_user_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="原始用户数据快照",
        ),
        sa.Column(
            "deletion_reason", sa.String(255), nullable=True, comment="删除原因"
        ),
        sa.Column(
            "deletion_type",
            sa.String(50),
            nullable=False,
            default="user_requested",
            comment="删除类型：user_requested, admin_deletion, compliance",
        ),
        sa.Column(
            "anonymized_fields",
            postgresql.ARRAY(sa.String()),
            nullable=True,
            comment="已匿名化的字段列表",
        ),
        sa.Column(
            "subscription_status_at_deletion",
            sa.String(50),
            nullable=True,
            comment="删除时订阅状态",
        ),
        sa.Column(
            "related_data_action",
            sa.String(100),
            nullable=True,
            comment="关联数据处理方式",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="日志创建时间",
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="处理完成时间",
        ),
        sa.Column(
            "processor_id",
            sa.String(),
            nullable=True,
            comment="处理者ID（用户本人或管理员）",
        ),
        comment="用户删除审计日志表",
    )

    # Add indexes
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    op.create_index("ix_users_anonymized_at", "users", ["anonymized_at"])
    op.create_index(
        "ix_user_deletion_logs_user_id", "user_deletion_logs", ["user_id"]
    )
    op.create_index(
        "ix_user_deletion_logs_created_at", "user_deletion_logs", ["created_at"]
    )


def downgrade() -> None:
    # Remove indexes
    op.drop_index(
        "ix_user_deletion_logs_created_at", table_name="user_deletion_logs"
    )
    op.drop_index(
        "ix_user_deletion_logs_user_id", table_name="user_deletion_logs"
    )
    op.drop_index("ix_users_anonymized_at", table_name="users")
    op.drop_index("ix_users_deleted_at", table_name="users")

    # Drop audit table
    op.drop_table("user_deletion_logs")

    # Remove columns from users table
    op.drop_column("users", "deletion_reason")
    op.drop_column("users", "anonymized_at")
    op.drop_column("users", "deleted_at")
