"""add readable_id to agents

Revision ID: 20250129_120000
Revises: 20250625_154455
Create Date: 2025-01-29 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20250129_120000"
down_revision = "20250625_154455"
branch_labels = None
depends_on = None


def upgrade():
    # 为agents表添加readable_id字段，暂时允许为空
    op.add_column(
        "agents", sa.Column("readable_id", sa.String(8), nullable=True)
    )

    # 创建索引（暂时不设置unique约束）
    op.create_index("ix_agents_readable_id", "agents", ["readable_id"])

    # 为现有记录生成readable_id
    connection = op.get_bind()
    result = connection.execute(
        text("SELECT id FROM agents ORDER BY created_at")
    )
    agents = result.fetchall()

    readable_id_counter = 10000000
    for agent in agents:
        connection.execute(
            text("UPDATE agents SET readable_id = :readable_id WHERE id = :id"),
            {"readable_id": str(readable_id_counter).zfill(8), "id": agent[0]},
        )
        readable_id_counter += 1

    # 修改字段为NOT NULL和UNIQUE
    op.alter_column("agents", "readable_id", nullable=False)
    op.create_unique_constraint(
        "uq_agents_readable_id", "agents", ["readable_id"]
    )


def downgrade():
    # 移除唯一约束
    op.drop_constraint("uq_agents_readable_id", "agents", type_="unique")

    # 移除索引
    op.drop_index("ix_agents_readable_id", "agents")

    # 移除readable_id字段
    op.drop_column("agents", "readable_id")
