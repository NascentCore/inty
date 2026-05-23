"""更新订阅权益功能

Revision ID: 72a30085032d
Revises: 20250130_140000_add_readable_id_to_users
Create Date: 2025-07-08 08:32:52.853540

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "72a30085032d"
down_revision: Union[str, None] = "20250703_130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """更新订阅权益功能"""
    # 定义权益功能
    premium_features = {
        "features": [
            {
                "key": "unlimited_messages",
                "name": "聊天无限制",
                "description": "无限制聊天消息数量",
                "type": "real",
                "icon": "💬",
                "order": 1,
            },
            {
                "key": "premium_model_usage",
                "name": "高级模型使用",
                "description": "使用更先进的AI模型",
                "type": "fake",
                "icon": "🧠",
                "order": 2,
            },
            {
                "key": "extra_chat_inspiration",
                "name": "更多聊天灵感",
                "description": "获得更多聊天话题建议",
                "type": "fake",
                "icon": "💡",
                "order": 3,
            },
            {
                "key": "customize_ai_responses",
                "name": "自定义更好的ai回复",
                "description": "个性化AI回复风格",
                "type": "fake",
                "icon": "🎨",
                "order": 4,
            },
            {
                "key": "chat_memory",
                "name": "聊天记忆",
                "description": "AI记住聊天历史上下文",
                "type": "fake",
                "icon": "🧠",
                "order": 5,
            },
            {
                "key": "new_features_privilege",
                "name": "体验新功能特权",
                "description": "优先体验最新功能",
                "type": "fake",
                "icon": "🚀",
                "order": 6,
            },
        ],
        "real_features": ["unlimited_messages"],
        "fake_features": [
            "premium_model_usage",
            "extra_chat_inspiration",
            "customize_ai_responses",
            "chat_memory",
            "new_features_privilege",
        ],
    }

    # 更新所有现有订阅计划的features字段
    connection = op.get_bind()

    # 更新所有订阅计划
    import json

    connection.execute(
        sa.text("""
        UPDATE subscription_plans 
        SET features = CAST(:features AS json)
        WHERE features IS NULL OR features::text = '{}'
        """),
        {"features": json.dumps(premium_features)},
    )

    # 如果需要，也可以为特定的订阅计划设置不同的features
    # 这里为所有计划设置相同的premium features


def downgrade() -> None:
    """回滚订阅权益功能更新"""
    # 清空features字段
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE subscription_plans SET features = '{}'::json")
    )
