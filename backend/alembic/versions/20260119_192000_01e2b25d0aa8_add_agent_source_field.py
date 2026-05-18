"""add agent source field

Revision ID: 01e2b25d0aa8
Revises: 83f37ed3d576
Create Date: 2026-01-19 19:20:00.000000+00:00

CREATED_BY_AGENT
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "01e2b25d0aa8"
down_revision: Union[str, None] = "83f37ed3d576"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 enum 类型
    agentsource_enum = sa.Enum("USER_CREATED", "AUTO_GENERATED", name="agentsource")
    agentsource_enum.create(op.get_bind(), checkfirst=True)

    # 添加 source 列
    op.add_column(
        "agents",
        sa.Column(
            "source",
            agentsource_enum,
            nullable=True,
            server_default="USER_CREATED",
            comment="角色来源：用户创建或自动生成",
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "source")

    # 删除 enum 类型
    agentsource_enum = sa.Enum("USER_CREATED", "AUTO_GENERATED", name="agentsource")
    agentsource_enum.drop(op.get_bind(), checkfirst=True)
