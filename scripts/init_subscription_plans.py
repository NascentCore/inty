#!/usr/bin/env python3
"""
初始化订阅计划脚本
创建月付、季付、年付三种订阅计划
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.services.subscription_service import subscription_service
from app.schemas.subscription import SubscriptionPlanCreate
from app.models.subscription import SubscriptionPlanType


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
            "features": {
                "features": [
                    {
                        "key": "unlimited_messages",
                        "name": "聊天无限制",
                        "description": "无限制聊天消息数量",
                        "type": "real",
                        "icon": "💬",
                        "order": 1
                    },
                    {
                        "key": "premium_model_usage",
                        "name": "高级模型使用",
                        "description": "使用更先进的AI模型",
                        "type": "fake",
                        "icon": "🧠",
                        "order": 2
                    },
                    {
                        "key": "extra_chat_inspiration",
                        "name": "更多聊天灵感",
                        "description": "获得更多聊天话题建议",
                        "type": "fake",
                        "icon": "💡",
                        "order": 3
                    },
                    {
                        "key": "customize_ai_responses",
                        "name": "自定义更好的ai回复",
                        "description": "个性化AI回复风格",
                        "type": "fake",
                        "icon": "🎨",
                        "order": 4
                    },
                    {
                        "key": "chat_memory",
                        "name": "聊天记忆",
                        "description": "AI记住聊天历史上下文",
                        "type": "fake",
                        "icon": "🧠",
                        "order": 5
                    },
                    {
                        "key": "new_features_privilege",
                        "name": "体验新功能特权",
                        "description": "优先体验最新功能",
                        "type": "fake",
                        "icon": "🚀",
                        "order": 6
                    }
                ],
                "real_features": ["unlimited_messages"],
                "fake_features": [
                    "premium_model_usage",
                    "extra_chat_inspiration", 
                    "customize_ai_responses",
                    "chat_memory",
                    "new_features_privilege"
                ]
            },
            "chat_limit_per_day": -1,  # 无限制
            "agent_creation_limit": 50,
            "is_active": True,
            "sort_order": 1
        },
        {
            "id": "premium_quarterly",
            "name": "Premium Quarterly",
            "description": "季度高级订阅，无聊天次数限制，更多Agent创建权限，季度优惠",
            "plan_type": SubscriptionPlanType.QUARTERLY,
            "price": 24.99,  # 相比月付每月8.33，节省17%
            "currency": "USD",
            "google_play_product_id": "com.ai.inty.premium.quarterly",
            "features": {
                "features": [
                    {
                        "key": "unlimited_messages",
                        "name": "聊天无限制",
                        "description": "无限制聊天消息数量",
                        "type": "real",
                        "icon": "💬",
                        "order": 1
                    },
                    {
                        "key": "premium_model_usage",
                        "name": "高级模型使用",
                        "description": "使用更先进的AI模型",
                        "type": "fake",
                        "icon": "🧠",
                        "order": 2
                    },
                    {
                        "key": "extra_chat_inspiration",
                        "name": "更多聊天灵感",
                        "description": "获得更多聊天话题建议",
                        "type": "fake",
                        "icon": "💡",
                        "order": 3
                    },
                    {
                        "key": "customize_ai_responses",
                        "name": "自定义更好的ai回复",
                        "description": "个性化AI回复风格",
                        "type": "fake",
                        "icon": "🎨",
                        "order": 4
                    },
                    {
                        "key": "chat_memory",
                        "name": "聊天记忆",
                        "description": "AI记住聊天历史上下文",
                        "type": "fake",
                        "icon": "🧠",
                        "order": 5
                    },
                    {
                        "key": "new_features_privilege",
                        "name": "体验新功能特权",
                        "description": "优先体验最新功能",
                        "type": "fake",
                        "icon": "🚀",
                        "order": 6
                    }
                ],
                "real_features": ["unlimited_messages"],
                "fake_features": [
                    "premium_model_usage",
                    "extra_chat_inspiration", 
                    "customize_ai_responses",
                    "chat_memory",
                    "new_features_privilege"
                ]
            },
            "chat_limit_per_day": -1,  # 无限制
            "agent_creation_limit": 75,
            "is_active": True,
            "sort_order": 2
        },
        {
            "id": "premium_yearly",
            "name": "Premium Yearly",
            "description": "年度高级订阅，无聊天次数限制，最多Agent创建权限，年度最优惠",
            "plan_type": SubscriptionPlanType.YEARLY,
            "price": 79.99,  # 相比月付每月6.67，节省33%
            "currency": "USD",
            "google_play_product_id": "com.ai.inty.premium.annual",
            "features": {
                "features": [
                    {
                        "key": "unlimited_messages",
                        "name": "聊天无限制",
                        "description": "无限制聊天消息数量",
                        "type": "real",
                        "icon": "💬",
                        "order": 1
                    },
                    {
                        "key": "premium_model_usage",
                        "name": "高级模型使用",
                        "description": "使用更先进的AI模型",
                        "type": "fake",
                        "icon": "🧠",
                        "order": 2
                    },
                    {
                        "key": "extra_chat_inspiration",
                        "name": "更多聊天灵感",
                        "description": "获得更多聊天话题建议",
                        "type": "fake",
                        "icon": "💡",
                        "order": 3
                    },
                    {
                        "key": "customize_ai_responses",
                        "name": "自定义更好的ai回复",
                        "description": "个性化AI回复风格",
                        "type": "fake",
                        "icon": "🎨",
                        "order": 4
                    },
                    {
                        "key": "chat_memory",
                        "name": "聊天记忆",
                        "description": "AI记住聊天历史上下文",
                        "type": "fake",
                        "icon": "🧠",
                        "order": 5
                    },
                    {
                        "key": "new_features_privilege",
                        "name": "体验新功能特权",
                        "description": "优先体验最新功能",
                        "type": "fake",
                        "icon": "🚀",
                        "order": 6
                    }
                ],
                "real_features": ["unlimited_messages"],
                "fake_features": [
                    "premium_model_usage",
                    "extra_chat_inspiration", 
                    "customize_ai_responses",
                    "chat_memory",
                    "new_features_privilege"
                ]
            },
            "chat_limit_per_day": -1,  # 无限制
            "agent_creation_limit": 100,
            "is_active": True,
            "sort_order": 3
        }
    ]
    
    async with AsyncSessionLocal() as db:
        try:
            print("开始初始化订阅计划...")
            
            for plan_data in subscription_plans:
                try:
                    # 检查计划是否已存在
                    existing_plan = await subscription_service.get_subscription_plan_by_id(
                        db, plan_data["id"]
                    )
                    
                    if existing_plan:
                        print(f"订阅计划 {plan_data['name']} 已存在，跳过...")
                        continue
                    
                    # 创建订阅计划
                    plan_create = SubscriptionPlanCreate(**plan_data)
                    created_plan = await subscription_service.create_subscription_plan(
                        db, plan_create
                    )
                    
                    print(f"✅ 成功创建订阅计划: {created_plan.name}")
                    print(f"   - ID: {created_plan.id}")
                    print(f"   - 类型: {created_plan.plan_type}")
                    print(f"   - 价格: {created_plan.price} {created_plan.currency}")
                    print(f"   - Google Play Product ID: {created_plan.google_play_product_id}")
                    print(f"   - 聊天限制: {created_plan.chat_limit_per_day}")
                    print(f"   - Agent创建限制: {created_plan.agent_creation_limit}")
                    print()
                    
                except Exception as e:
                    print(f"❌ 创建订阅计划 {plan_data['name']} 失败: {str(e)}")
                    continue
            
            print("订阅计划初始化完成！")
            
        except Exception as e:
            print(f"❌ 初始化订阅计划失败: {str(e)}")
            raise


async def list_subscription_plans():
    """列出所有订阅计划"""
    async with AsyncSessionLocal() as db:
        try:
            plans = await subscription_service.get_subscription_plans(db, include_inactive=True)
            
            print("当前所有订阅计划:")
            print("=" * 50)
            
            for plan in plans:
                print(f"ID: {plan.id}")
                print(f"名称: {plan.name}")
                print(f"类型: {plan.plan_type}")
                print(f"价格: {plan.price} {plan.currency}")
                print(f"Google Play Product ID: {plan.google_play_product_id}")
                print(f"聊天限制: {plan.chat_limit_per_day}")
                print(f"Agent创建限制: {plan.agent_creation_limit}")
                print(f"是否激活: {plan.is_active}")
                print(f"创建时间: {plan.created_at}")
                print("-" * 30)
                
        except Exception as e:
            print(f"❌ 获取订阅计划失败: {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="订阅计划管理脚本")
    parser.add_argument("--action", choices=["init", "list"], default="init", 
                       help="执行的操作: init=初始化计划, list=列出计划")
    
    args = parser.parse_args()
    
    if args.action == "init":
        asyncio.run(init_subscription_plans())
    elif args.action == "list":
        asyncio.run(list_subscription_plans()) 