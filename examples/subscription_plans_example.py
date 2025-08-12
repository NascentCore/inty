#!/usr/bin/env python3
"""
Example of creating SubscriptionPlan objects from real database data
"""

from app.core.config import SubscriptionPlan


def create_subscription_plans_from_db_data():
    """Create SubscriptionPlan objects from the database data"""

    # Premium Monthly Plan
    premium_monthly = SubscriptionPlan(
        id="premium_monthly",
        name="Monthly",
        description="月度高级订阅，无聊天次数限制，更多Agent创建权限",
        plan_type="MONTHLY",
        price=9.99,
        currency="USD",
        google_play_product_id="com.ai.intellimate.premium.monthly",
        discount_rate=1.0,
        features={
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
        },
        chat_limit_per_day=-1,  # 无限制
        agent_creation_limit=50,
        background_generation_limit_per_day=3,
        is_active=True,
        sort_order=1,
    )

    # Premium Yearly Plan
    premium_yearly = SubscriptionPlan(
        id="premium_yearly",
        name="Yearly",
        description="年度高级订阅，无聊天次数限制，最多Agent创建权限，年度最优惠",
        plan_type="YEARLY",
        price=79.99,
        currency="USD",
        google_play_product_id="com.ai.intellimate.premium.annual",
        discount_rate=0.5,  # 年度优惠50%
        features={
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
        },
        chat_limit_per_day=-1,  # 无限制
        agent_creation_limit=100,
        background_generation_limit_per_day=3,
        is_active=True,
        sort_order=3,
    )

    # Premium Quarterly Plan
    premium_quarterly = SubscriptionPlan(
        id="premium_quarterly",
        name="Quarterly",
        description="季度高级订阅，无聊天次数限制，更多Agent创建权限，季度优惠",
        plan_type="QUARTERLY",
        price=24.99,
        currency="USD",
        google_play_product_id="com.ai.intellimate.premium.quarterly",
        discount_rate=0.5,  # 季度优惠50%
        features={
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
        },
        chat_limit_per_day=-1,  # 无限制
        agent_creation_limit=75,
        background_generation_limit_per_day=3,
        is_active=True,
        sort_order=2,
    )

    return [premium_monthly, premium_yearly, premium_quarterly]


def print_subscription_plan_details(plan: SubscriptionPlan):
    """Print detailed information about a subscription plan"""
    print(f"\n{'='*60}")
    print(f"Subscription Plan: {plan.name}")
    print(f"{'='*60}")
    print(f"ID: {plan.id}")
    print(f"Description: {plan.description}")
    print(f"Type: {plan.plan_type}")
    print(f"Price: {plan.price} {plan.currency}")
    print(f"Google Play Product ID: {plan.google_play_product_id}")
    print(f"Discount Rate: {plan.discount_rate}")
    print(f"Chat Limit Per Day: {plan.chat_limit_per_day}")
    print(f"Agent Creation Limit: {plan.agent_creation_limit}")
    print(f"Background Generation Limit: {plan.background_generation_limit_per_day}")
    print(f"Is Active: {plan.is_active}")
    print(f"Sort Order: {plan.sort_order}")

    print(f"\nFeatures:")
    if plan.features and "features" in plan.features:
        for feature in plan.features["features"]:
            feature_type = "✅ REAL" if feature["type"] == "real" else "❌ FAKE"
            print(
                f"  {feature_type} - {feature['name']}: {feature['description']} {feature['icon']}"
            )

    if plan.features and "real_features" in plan.features:
        print(f"\nReal Features: {', '.join(plan.features['real_features'])}")

    if plan.features and "fake_features" in plan.features:
        print(f"Fake Features: {', '.join(plan.features['fake_features'])}")


def main():
    """Main function to demonstrate subscription plan creation"""
    print("Creating SubscriptionPlan objects from database data...")

    # Create the subscription plans
    plans = create_subscription_plans_from_db_data()

    # Print details for each plan
    for plan in plans:
        print_subscription_plan_details(plan)

    print(f"\n{'='*60}")
    print(f"Total Plans Created: {len(plans)}")
    print(f"{'='*60}")

    # Example of accessing specific plan properties
    monthly_plan = next(p for p in plans if p.id == "premium_monthly")
    print(
        f"\nExample - Monthly Plan Agent Creation Limit: {monthly_plan.agent_creation_limit}"
    )

    # Example of checking if a plan has unlimited chat
    unlimited_plans = [p for p in plans if p.chat_limit_per_day == -1]
    print(f"Plans with unlimited chat: {len(unlimited_plans)}")

    # Example of finding plans by type
    yearly_plans = [p for p in plans if p.plan_type == "YEARLY"]
    print(f"Yearly plans: {len(yearly_plans)}")


if __name__ == "__main__":
    main()
