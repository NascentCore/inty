"""add evaluation system tables

Revision ID: 20250726_001000
Revises: 41ce4e778dd4
Create Date: 2025-07-26 00:10:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250726_001000"
down_revision = "41ce4e778dd4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create evaluation_sessions table
    op.create_table(
        "evaluation_sessions",
        sa.Column("id", sa.String(), nullable=False, comment="评测会话ID"),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
            comment="评测会话名称",
        ),
        sa.Column(
            "creator_id", sa.String(), nullable=False, comment="创建者ID"
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                name="evaluation_status",
            ),
            nullable=False,
            comment="评测状态",
        ),
        sa.Column(
            "questions",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="测试问题列表",
        ),
        sa.Column(
            "selected_agents",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="选中的智能体ID列表",
        ),
        sa.Column(
            "scoring_model",
            sa.String(length=255),
            nullable=False,
            comment="评分模型",
        ),
        sa.Column(
            "scoring_criteria", sa.Text(), nullable=True, comment="评分标准"
        ),
        sa.Column(
            "use_new_user_identity",
            sa.Boolean(),
            nullable=False,
            comment="是否使用新用户身份",
        ),
        sa.Column(
            "config",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="其他配置参数",
        ),
        sa.Column(
            "total_tests", sa.Integer(), nullable=False, comment="总测试数量"
        ),
        sa.Column(
            "completed_tests",
            sa.Integer(),
            nullable=False,
            comment="已完成测试数量",
        ),
        sa.Column("success_rate", sa.Float(), nullable=True, comment="成功率"),
        sa.Column(
            "average_score", sa.Float(), nullable=True, comment="平均分数"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="开始时间",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="完成时间",
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_sessions_id"),
        "evaluation_sessions",
        ["id"],
        unique=False,
    )

    # Create evaluation_results table
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False, comment="测试问题"),
        sa.Column(
            "question_index", sa.Integer(), nullable=False, comment="问题序号"
        ),
        sa.Column(
            "agent_response", sa.Text(), nullable=True, comment="智能体回复"
        ),
        sa.Column(
            "response_time", sa.Float(), nullable=True, comment="回复时间(秒)"
        ),
        sa.Column("overall_score", sa.Float(), nullable=True, comment="总分"),
        sa.Column(
            "detailed_scores",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="详细评分 {dimension: score}",
        ),
        sa.Column(
            "scoring_reason", sa.Text(), nullable=True, comment="评分理由"
        ),
        sa.Column(
            "scoring_model_used",
            sa.String(length=255),
            nullable=True,
            comment="使用的评分模型",
        ),
        sa.Column(
            "is_success", sa.Boolean(), nullable=False, comment="是否成功完成"
        ),
        sa.Column(
            "error_message", sa.Text(), nullable=True, comment="错误信息"
        ),
        sa.Column(
            "extra_data",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="其他元数据",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["evaluation_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_results_id"),
        "evaluation_results",
        ["id"],
        unique=False,
    )

    # Create evaluation_interactions table
    op.create_table(
        "evaluation_interactions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("result_id", sa.String(), nullable=False),
        sa.Column(
            "chat_id", sa.String(), nullable=True, comment="关联的聊天会话ID"
        ),
        sa.Column("user_input", sa.Text(), nullable=True, comment="用户输入"),
        sa.Column(
            "agent_response", sa.Text(), nullable=True, comment="智能体回复"
        ),
        sa.Column(
            "interaction_order", sa.Integer(), nullable=True, comment="交互顺序"
        ),
        sa.Column(
            "user_identity",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="用户身份信息",
        ),
        sa.Column(
            "response_metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="回复元数据",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["chats.id"],
        ),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["evaluation_results.id"],
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["evaluation_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_interactions_id"),
        "evaluation_interactions",
        ["id"],
        unique=False,
    )

    # Create evaluation_templates table
    op.create_table(
        "evaluation_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "name", sa.String(length=255), nullable=False, comment="模板名称"
        ),
        sa.Column("description", sa.Text(), nullable=True, comment="模板描述"),
        sa.Column("creator_id", sa.String(), nullable=False),
        sa.Column(
            "questions",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="问题列表",
        ),
        sa.Column(
            "default_scoring_criteria",
            sa.Text(),
            nullable=True,
            comment="默认评分标准",
        ),
        sa.Column(
            "recommended_models",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="推荐的评分模型",
        ),
        sa.Column(
            "config",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="模板配置",
        ),
        sa.Column(
            "tags",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="标签",
        ),
        sa.Column(
            "usage_count", sa.Integer(), nullable=False, comment="使用次数"
        ),
        sa.Column(
            "is_public", sa.Boolean(), nullable=False, comment="是否公开"
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, comment="是否活跃"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_templates_id"),
        "evaluation_templates",
        ["id"],
        unique=False,
    )

    # Add default values
    op.execute(
        "ALTER TABLE evaluation_sessions ALTER COLUMN status SET DEFAULT 'PENDING'"
    )
    op.execute(
        "ALTER TABLE evaluation_sessions ALTER COLUMN use_new_user_identity SET DEFAULT false"
    )
    op.execute(
        "ALTER TABLE evaluation_sessions ALTER COLUMN total_tests SET DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE evaluation_sessions ALTER COLUMN completed_tests SET DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE evaluation_results ALTER COLUMN is_success SET DEFAULT true"
    )
    op.execute(
        "ALTER TABLE evaluation_templates ALTER COLUMN usage_count SET DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE evaluation_templates ALTER COLUMN is_public SET DEFAULT false"
    )
    op.execute(
        "ALTER TABLE evaluation_templates ALTER COLUMN is_active SET DEFAULT true"
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_evaluation_templates_id"), table_name="evaluation_templates"
    )
    op.drop_table("evaluation_templates")
    op.drop_index(
        op.f("ix_evaluation_interactions_id"),
        table_name="evaluation_interactions",
    )
    op.drop_table("evaluation_interactions")
    op.drop_index(
        op.f("ix_evaluation_results_id"), table_name="evaluation_results"
    )
    op.drop_table("evaluation_results")
    op.drop_index(
        op.f("ix_evaluation_sessions_id"), table_name="evaluation_sessions"
    )
    op.drop_table("evaluation_sessions")
    op.execute("DROP TYPE IF EXISTS evaluation_status")
