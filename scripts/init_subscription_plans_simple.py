#!/usr/bin/env python3
"""
简化版订阅计划初始化脚本
直接操作数据库，不依赖Google Play服务
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.models.subscription import SubscriptionPlan, SubscriptionPlanType


async def create_subscription_plan_direct(db: AsyncSession, plan_data: dict):
    """直接创建订阅计划到数据库"""
    try:
        # 检查是否已存在
        existing_plan = await db.get(SubscriptionPlan, plan_data["id"])
        if existing_plan:
            print(f"订阅计划 {plan_data['name']} 已存在，跳过...")
            return existing_plan

        # 创建新的订阅计划
        plan = SubscriptionPlan(
            id=plan_data["id"],
            name=plan_data["name"],
            description=plan_data["description"],
            plan_type=plan_data["plan_type"],
            price=plan_data["price"],
            currency=plan_data["currency"],
            google_play_product_id=plan_data["google_play_product_id"],
            discount_rate=plan_data.get("discount_rate", 1.0),
            features=plan_data["features"],
            chat_limit_per_day=plan_data["chat_limit_per_day"],
            agent_creation_limit=plan_data["agent_creation_limit"],
            background_generation_limit_per_day=plan_data.get(
                "background_generation_limit_per_day", 3
            ),
            is_active=plan_data["is_active"],
            sort_order=plan_data["sort_order"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        return plan

    except Exception as e:
        await db.rollback()
        print(f"创建订阅计划失败: {str(e)}")
        raise


async def init_subscription_plans():
    """初始化三种订阅计划"""

    subscription_plans = [
        {
            "id": "premium_monthly",
            "name": "Premium Monthly",
            "description": "月度高级订阅，无聊天次数限制，更多Agent创建权限",
            "plan_type": SubscriptionPlanType.MONTHLY,
            "price": 9.99,
            "currency": "USD",
            "google_play_product_id": "com.ai.inty.premium.monthly",
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
            "name": "Premium Quarterly",
            "description": "季度高级订阅，无聊天次数限制，更多Agent创建权限，季度优惠",
            "plan_type": SubscriptionPlanType.QUARTERLY,
            "price": 24.99,  # 相比月付每月8.33，节省17%
            "currency": "USD",
            "google_play_product_id": "com.ai.inty.premium.quarterly",
            "discount_rate": 0.9,  # 9折优惠
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
            "name": "Premium Yearly",
            "description": "年度高级订阅，无聊天次数限制，最多Agent创建权限，年度最优惠",
            "plan_type": SubscriptionPlanType.YEARLY,
            "price": 79.99,  # 相比月付每月6.67，节省33%
            "currency": "USD",
            "google_play_product_id": "com.ai.inty.premium.annual",
            "discount_rate": 0.8,  # 8折优惠
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
        try:
            print("开始初始化订阅计划...")
            print("=" * 50)

            for plan_data in subscription_plans:
                try:
                    created_plan = await create_subscription_plan_direct(db, plan_data)

                    print(f"✅ 订阅计划: {created_plan.name}")
                    print(f"   - ID: {created_plan.id}")
                    print(f"   - 类型: {created_plan.plan_type}")
                    print(f"   - 价格: {created_plan.price} {created_plan.currency}")
                    print(
                        f"   - Google Play Product ID: {created_plan.google_play_product_id}"
                    )
                    print(f"   - 聊天限制: {created_plan.chat_limit_per_day}")
                    print(f"   - Agent创建限制: {created_plan.agent_creation_limit}")
                    print()

                except Exception as e:
                    print(f"❌ 创建订阅计划 {plan_data['name']} 失败: {str(e)}")
                    continue

            print("订阅计划初始化完成！")
            print("=" * 50)

        except Exception as e:
            print(f"❌ 初始化订阅计划失败: {str(e)}")
            raise


async def list_subscription_plans():
    """列出所有订阅计划"""
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select

            # 查询所有订阅计划
            result = await db.execute(select(SubscriptionPlan))
            plans = result.scalars().all()

            print("当前所有订阅计划:")
            print("=" * 80)

            for plan in plans:
                print(f"ID: {plan.id}")
                print(f"名称: {plan.name}")
                print(f"描述: {plan.description}")
                print(f"类型: {plan.plan_type}")
                print(f"价格: {plan.price} {plan.currency}")
                print(f"Google Play Product ID: {plan.google_play_product_id}")
                print(f"聊天限制: {plan.chat_limit_per_day}")
                print(f"Agent创建限制: {plan.agent_creation_limit}")
                print(f"是否激活: {plan.is_active}")
                print(f"排序: {plan.sort_order}")
                print(f"创建时间: {plan.created_at}")
                print(f"功能特性: {plan.features}")
                print("-" * 80)

        except Exception as e:
            print(f"❌ 获取订阅计划失败: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="订阅计划管理脚本（简化版）")
    parser.add_argument(
        "--action",
        choices=["init", "list"],
        default="init",
        help="执行的操作: init=初始化计划, list=列出计划",
    )

    args = parser.parse_args()

    if args.action == "init":
        asyncio.run(init_subscription_plans())
    elif args.action == "list":
        asyncio.run(list_subscription_plans())
