"""add fcm_token_invalid_at to users

Revision ID: 20251114_142810
Revises: 15551f22eef0
Create Date: 2025-11-14 14:28:10.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251114_142810"
down_revision = "15551f22eef0"
branch_labels = None
depends_on = None


def upgrade():
    # 为 users 表添加 fcm_token_invalid_at 字段
    op.add_column(
        "users",
        sa.Column(
            "fcm_token_invalid_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="FCM token 无效时间，如果为 None 表示用户有有效 token 或未检查，如果有值表示在这个时间点发现用户所有 token 都无效",
        ),
    )


def downgrade():
    # 移除 fcm_token_invalid_at 字段
    op.drop_column("users", "fcm_token_invalid_at")
