"""add deleted_at to agents

Revision ID: 20250625_154455
Revises: 474e96b4de1b
Create Date: 2025-06-25 15:44:55.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250625_154455"
down_revision = "474e96b4de1b"
branch_labels = None
depends_on = None


def upgrade():
    # 为agents表添加deleted_at字段
    op.add_column(
        "agents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    # 移除deleted_at字段
    op.drop_column("agents", "deleted_at")
