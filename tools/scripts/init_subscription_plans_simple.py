#!/usr/bin/env python3
"""
简化版订阅计划初始化脚本
直接操作数据库，不依赖Google Play服务
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.subscription import SubscriptionPlan, SubscriptionPlanType


async def create_subscription_plan_direct(db: AsyncSession, plan_data: dict):
    """直接创建或更新订阅计划到数据库"""
    existing_plan = await db.get(SubscriptionPlan, plan_data["id"])
    if existing_plan:
        print(f"订阅计划 {plan_data['name']} 已存在，更新字段...")
        # 自动化更新现有计划的字段
        for key, value in plan_data.items():
            if key != "id" and hasattr(existing_plan, key):
                setattr(existing_plan, key, value)

        # 设置默认值
        if (
            not hasattr(existing_plan, "discount_rate")
            or existing_plan.discount_rate is None
        ):
            existing_plan.discount_rate = plan_data.get("discount_rate", 1.0)
        if (
            not hasattr(existing_plan, "background_generation_limit_per_day")
            or existing_plan.background_generation_limit_per_day is None
        ):
            existing_plan.background_generation_limit_per_day = plan_data.get(
                "background_generation_limit_per_day", 3
            )

        existing_plan.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(existing_plan)
        return existing_plan

    # 创建新的订阅计划
    # 准备创建数据，设置默认值
    create_data = plan_data.copy()
    create_data.setdefault("discount_rate", 1.0)
    create_data.setdefault("background_generation_limit_per_day", 3)
    create_data["created_at"] = datetime.now(UTC)
    create_data["updated_at"] = datetime.now(UTC)

    plan = SubscriptionPlan(**create_data)

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return plan


async def init_subscription_plans():
    """初始化或更新三种订阅计划"""

    subscription_plans = [
        {
            "id": "premium_monthly",
            "name": "Monthly",
            "description": "月度高级订阅，无聊天次数限制，更多Agent创建权限",
            "plan_type": SubscriptionPlanType.MONTHLY,
            "price": 9.99,
            "currency": "USD",
            "google_play_product_id": "com.ai.intellimate.premium.monthly",
            "discount_rate": 1.0,  # 无折扣
            "features": {
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
            "chat_limit_per_day": -1,  # 无限制
            "agent_creation_limit": 50,
            "background_generation_limit_per_day": -1,  # 无限制
            "is_active": True,
            "sort_order": 1,
        },
        {
            "id": "premium_quarterly",
            "name": "Quarterly",
            "description": "季度高级订阅，无聊天次数限制，更多Agent创建权限，季度优惠",
            "plan_type": SubscriptionPlanType.QUARTERLY,
            "price": 19.99,  # 相比月付每月8.33，节省17%
            "currency": "USD",
            "google_play_product_id": "com.ai.intellimate.premium.quarterly",
            "discount_rate": 0.673,
            "features": {
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
            "chat_limit_per_day": -1,  # 无限制
            "agent_creation_limit": 75,
            "background_generation_limit_per_day": -1,  # 无限制
            "is_active": True,
            "sort_order": 2,
        },
        {
            "id": "premium_yearly",
            "name": "Annually",
            "description": "年度高级订阅，无聊天次数限制，最多Agent创建权限，年度最优惠",
            "plan_type": SubscriptionPlanType.YEARLY,
            "price": 59.99,  # 相比月付每月6.67，节省33%
            "currency": "USD",
            "google_play_product_id": "com.ai.intellimate.premium.annual",
            "discount_rate": 0.505,
            "features": {
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
            "chat_limit_per_day": -1,  # 无限制
            "agent_creation_limit": 100,
            "background_generation_limit_per_day": -1,  # 无限制
            "is_active": True,
            "sort_order": 3,
        },
    ]

    async with AsyncSessionLocal() as db:
        print("开始初始化/更新订阅计划...")
        print("=" * 50)

        for plan_data in subscription_plans:
            created_plan = await create_subscription_plan_direct(db, plan_data)

            print(f"✅ 订阅计划: {created_plan.name}")
            print(f"   - ID: {created_plan.id}")
            print(f"   - 类型: {created_plan.plan_type}")
            print(f"   - 价格: {created_plan.price} {created_plan.currency}")
            print(f"   - Google Play Product ID: {created_plan.google_play_product_id}")
            print(f"   - 聊天限制: {created_plan.chat_limit_per_day}")
            print(f"   - Agent创建限制: {created_plan.agent_creation_limit}")
            print()

        print("订阅计划初始化/更新完成！")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(init_subscription_plans())
