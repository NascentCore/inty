"""add character theme tables

Revision ID: 20251201_154257
Revises: ac1a943ddb73
Create Date: 2025-12-01 15:42:57.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251201_154257"
down_revision: Union[str, None] = "ac1a943ddb73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create character_themes table
    op.create_table(
        "character_themes",
        sa.Column("id", sa.String(), nullable=False, comment="专区ID"),
        sa.Column("name", sa.String(length=255), nullable=False, comment="专区名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="专区描述"),
        sa.Column(
            "background_image_url", sa.String(), nullable=True, comment="背景图URL地址"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_character_themes_id"), "character_themes", ["id"], unique=False
    )

    # Create character_theme_agents table
    op.create_table(
        "character_theme_agents",
        sa.Column("theme_id", sa.String(), nullable=False, comment="专区ID"),
        sa.Column("agent_id", sa.String(), nullable=False, comment="角色ID"),
        sa.Column(
            "order_index",
            sa.Integer(),
            nullable=False,
            comment="角色在专区中的顺序（从0开始）",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["theme_id"], ["character_themes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("theme_id", "agent_id"),
    )
    op.create_index(
        op.f("ix_character_theme_agents_theme_id"),
        "character_theme_agents",
        ["theme_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_character_theme_agents_order_index"),
        "character_theme_agents",
        ["order_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_character_theme_agents_order_index"),
        table_name="character_theme_agents",
    )
    op.drop_index(
        op.f("ix_character_theme_agents_theme_id"), table_name="character_theme_agents"
    )
    op.drop_table("character_theme_agents")
    op.drop_index(op.f("ix_character_themes_id"), table_name="character_themes")
    op.drop_table("character_themes")
