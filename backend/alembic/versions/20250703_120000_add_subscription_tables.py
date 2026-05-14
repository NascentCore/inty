"""add_subscription_tables

Revision ID: 20250703_120000
Revises: 20250130_140000
Create Date: 2025-07-03 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250703_120000"
down_revision: Union[str, None] = "20250130_140000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create subscription_plans table
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.String(), nullable=False, comment="计划ID"),
        sa.Column("name", sa.String(), nullable=False, comment="计划名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="计划描述"),
        sa.Column(
            "plan_type",
            sa.Enum("MONTHLY", "YEARLY", name="subscriptionplantype"),
            nullable=False,
            comment="计划类型",
        ),
        sa.Column("price", sa.Float(), nullable=False, comment="价格"),
        sa.Column("currency", sa.String(), nullable=True, comment="货币"),
        sa.Column(
            "google_play_product_id",
            sa.String(),
            nullable=False,
            comment="Google Play产品ID",
        ),
        sa.Column("features", sa.JSON(), nullable=True, comment="功能权益配置"),
        sa.Column(
            "chat_limit_per_day",
            sa.Integer(),
            nullable=True,
            comment="每日聊天次数限制，-1为无限制",
        ),
        sa.Column(
            "agent_creation_limit",
            sa.Integer(),
            nullable=True,
            comment="Agent创建数量限制",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=True, comment="是否激活"),
        sa.Column("sort_order", sa.Integer(), nullable=True, comment="排序顺序"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_play_product_id"),
        comment="订阅计划表",
    )
    op.create_index(
        op.f("ix_subscription_plans_id"), "subscription_plans", ["id"], unique=False
    )

    # Create user_subscriptions table
    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.String(), nullable=False, comment="订阅记录ID"),
        sa.Column("user_id", sa.String(), nullable=False, comment="用户ID"),
        sa.Column("plan_id", sa.String(), nullable=False, comment="订阅计划ID"),
        sa.Column(
            "google_play_purchase_token",
            sa.String(),
            nullable=True,
            comment="Google Play购买令牌",
        ),
        sa.Column(
            "google_play_order_id",
            sa.String(),
            nullable=True,
            comment="Google Play订单ID",
        ),
        sa.Column(
            "google_play_subscription_id",
            sa.String(),
            nullable=True,
            comment="Google Play订阅ID",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "EXPIRED",
                "CANCELLED",
                "PENDING",
                "REFUNDED",
                "GRACE_PERIOD",
                "PAUSED",
                name="subscriptionstatus",
            ),
            nullable=True,
            comment="订阅状态",
        ),
        sa.Column(
            "start_date", sa.DateTime(timezone=True), nullable=True, comment="开始时间"
        ),
        sa.Column(
            "end_date", sa.DateTime(timezone=True), nullable=True, comment="结束时间"
        ),
        sa.Column(
            "trial_end_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="试用结束时间",
        ),
        sa.Column("auto_renew", sa.Boolean(), nullable=True, comment="是否自动续费"),
        sa.Column("extra_data", sa.JSON(), nullable=True, comment="额外元数据"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["subscription_plans.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_play_purchase_token"),
        comment="用户订阅记录表",
    )
    op.create_index(
        op.f("ix_user_subscriptions_id"), "user_subscriptions", ["id"], unique=False
    )

    # Create subscription_transactions table
    op.create_table(
        "subscription_transactions",
        sa.Column("id", sa.String(), nullable=False, comment="交易记录ID"),
        sa.Column("subscription_id", sa.String(), nullable=False, comment="订阅记录ID"),
        sa.Column("user_id", sa.String(), nullable=False, comment="用户ID"),
        sa.Column(
            "transaction_type",
            sa.Enum(
                "PURCHASE",
                "RENEWAL",
                "UPGRADE",
                "DOWNGRADE",
                "REFUND",
                "CANCEL",
                name="transactiontype",
            ),
            nullable=False,
            comment="交易类型",
        ),
        sa.Column("amount", sa.Float(), nullable=False, comment="交易金额"),
        sa.Column("currency", sa.String(), nullable=True, comment="货币"),
        sa.Column(
            "google_play_purchase_token",
            sa.String(),
            nullable=True,
            comment="Google Play购买令牌",
        ),
        sa.Column(
            "google_play_order_id",
            sa.String(),
            nullable=True,
            comment="Google Play订单ID",
        ),
        sa.Column(
            "google_play_transaction_id",
            sa.String(),
            nullable=True,
            comment="Google Play交易ID",
        ),
        sa.Column("status", sa.String(), nullable=True, comment="交易状态"),
        sa.Column(
            "transaction_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="交易时间",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.Column("extra_data", sa.JSON(), nullable=True, comment="额外元数据"),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["user_subscriptions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="订阅交易记录表",
    )
    op.create_index(
        op.f("ix_subscription_transactions_id"),
        "subscription_transactions",
        ["id"],
        unique=False,
    )

    # Create subscription_usage table
    op.create_table(
        "subscription_usage",
        sa.Column("id", sa.String(), nullable=False, comment="使用记录ID"),
        sa.Column("user_id", sa.String(), nullable=False, comment="用户ID"),
        sa.Column("subscription_id", sa.String(), nullable=True, comment="订阅记录ID"),
        sa.Column(
            "usage_type",
            sa.String(),
            nullable=False,
            comment="使用类型（如chat、agent_creation等）",
        ),
        sa.Column(
            "usage_date", sa.DateTime(timezone=True), nullable=False, comment="使用日期"
        ),
        sa.Column("usage_count", sa.Integer(), nullable=True, comment="使用次数"),
        sa.Column("extra_data", sa.JSON(), nullable=True, comment="额外元数据"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
            comment="创建时间",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["user_subscriptions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="订阅使用记录表",
    )
    op.create_index(
        op.f("ix_subscription_usage_id"), "subscription_usage", ["id"], unique=False
    )

    # Insert default subscription plans
    op.execute("""
        INSERT INTO subscription_plans (id, name, description, plan_type, price, currency, google_play_product_id, features, chat_limit_per_day, agent_creation_limit, is_active, sort_order)
        VALUES 
        ('premium_monthly', 'Premium Monthly', '月度高级订阅，无聊天次数限制', 'MONTHLY', 9.99, 'USD', 'premium_monthly_v1', '{"unlimited_chat": true, "priority_support": true}', -1, 50, true, 1),
        ('premium_yearly', 'Premium Yearly', '年度高级订阅，无聊天次数限制', 'YEARLY', 99.99, 'USD', 'premium_yearly_v1', '{"unlimited_chat": true, "priority_support": true, "yearly_discount": true}', -1, 100, true, 2);
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f("ix_subscription_usage_id"), table_name="subscription_usage")
    op.drop_table("subscription_usage")

    op.drop_index(
        op.f("ix_subscription_transactions_id"), table_name="subscription_transactions"
    )
    op.drop_table("subscription_transactions")

    op.drop_index(op.f("ix_user_subscriptions_id"), table_name="user_subscriptions")
    op.drop_table("user_subscriptions")

    op.drop_index(op.f("ix_subscription_plans_id"), table_name="subscription_plans")
    op.drop_table("subscription_plans")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS subscriptionplantype")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS transactiontype")
