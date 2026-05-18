#!/usr/bin/env python3
"""
恢复用户订阅脚本

用于恢复由于前端问题导致订阅失败的用户订阅。
本脚本为 bobbyjackson150@googlemail.com 用户恢复月付会员订阅。
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.subscription import (
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTransaction,
    TransactionType,
    UserSubscription,
)
from app.models.user import User

# 用户信息
USER_EMAIL = "bobbyjackson150@googlemail.com"

# 订阅信息
PURCHASE_TOKEN = "bkeleepadcbbjkaanblkbfbb.AO-J1OzJtZ1UIzIVffU-aA3TpsSHMYMZZqCFIBwMRvxxcWtqnsdeuqfO8cKTPtkbJ5zk2xr5La1Jm6OKY9nT86Z-7iqDhckbAw"
ORDER_ID = "GPA.3399-1456-6599-70500"
PLAN_ID = "premium_monthly"  # 月付订阅计划ID
GOOGLE_PLAY_PRODUCT_ID = "com.ai.intellimate.premium.monthly"

# 时间信息（从图片中获取）
START_DATE = datetime(2025, 11, 5, 17, 59, 28, tzinfo=timezone.utc)
SUBSCRIPTION_DURATION_MONTHS = 1  # 1个月，与 Google Play 月付周期一致


async def find_user_by_email(db: AsyncSession, email: str) -> User:
    """通过邮箱查找用户"""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError(f"未找到邮箱为 {email} 的用户")

    return user


async def find_subscription_plan(
    db: AsyncSession, plan_id: str
) -> SubscriptionPlan:
    """查找订阅计划"""
    plan = await db.get(SubscriptionPlan, plan_id)

    if not plan:
        raise ValueError(f"未找到订阅计划: {plan_id}")

    return plan


async def check_existing_subscription(
    db: AsyncSession, purchase_token: str, order_id: str
) -> Optional[UserSubscription]:
    """检查是否已存在订阅记录"""
    # 先通过购买令牌查找
    stmt = select(UserSubscription).where(
        UserSubscription.google_play_purchase_token == purchase_token
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if subscription:
        logger.warning(f"已存在使用该购买令牌的订阅: {subscription.id}")
        return subscription

    # 再通过订单ID查找
    stmt = select(UserSubscription).where(
        UserSubscription.google_play_order_id == order_id
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if subscription:
        logger.warning(f"已存在使用该订单ID的订阅: {subscription.id}")
        return subscription

    return None


async def cancel_user_active_subscriptions(
    db: AsyncSession, user_id: str, dry_run: bool = False
) -> int:
    """取消用户当前的所有活跃订阅"""
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == user_id,
        UserSubscription.status == SubscriptionStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    active_subscriptions = result.scalars().all()

    count = 0
    for subscription in active_subscriptions:
        if dry_run:
            logger.info(f"[DRY RUN] 将取消活跃订阅: {subscription.id}")
        else:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.auto_renew = False
            logger.info(f"取消活跃订阅: {subscription.id}")
        count += 1

    if count > 0:
        if dry_run:
            logger.info(f"[DRY RUN] 将取消用户 {user_id} 的 {count} 个活跃订阅")
        else:
            await db.commit()
            logger.info(f"已取消用户 {user_id} 的 {count} 个活跃订阅")

    return count


async def create_subscription_record(
    db: AsyncSession,
    user: User,
    plan: SubscriptionPlan,
    purchase_token: str,
    order_id: str,
    start_date: datetime,
    duration_months: int,
    dry_run: bool = False,
) -> UserSubscription:
    """创建订阅记录"""
    import uuid

    # 计算结束时间
    end_date = start_date + timedelta(days=duration_months * 30)

    subscription_id = str(uuid.uuid4())
    subscription = UserSubscription(
        id=subscription_id,
        user_id=user.id,
        plan_id=plan.id,
        google_play_purchase_token=purchase_token,
        google_play_order_id=order_id,
        google_play_subscription_id=plan.google_play_product_id,
        status=SubscriptionStatus.ACTIVE,
        start_date=start_date,
        end_date=end_date,
        auto_renew=True,
        extra_data={
            "restored_manually": True,
            "restored_at": datetime.now(timezone.utc).isoformat(),
            "restored_reason": "前端问题导致订阅失败，手动恢复",
            "subscription_duration_months": duration_months,
        },
    )

    if dry_run:
        logger.info(f"[DRY RUN] 将创建订阅记录:")
        logger.info(f"  - 订阅ID: {subscription_id}")
        logger.info(f"  - 用户ID: {user.id}")
        logger.info(f"  - 计划ID: {plan.id}")
        logger.info(f"  - 状态: {SubscriptionStatus.ACTIVE}")
        logger.info(f"  - 开始时间: {start_date}")
        logger.info(f"  - 结束时间: {end_date}")
        logger.info(f"  - 自动续费: True")
    else:
        db.add(subscription)
        await db.flush()  # 获取 subscription.id
        logger.info(f"创建订阅记录: {subscription.id}")

    return subscription


async def create_transaction_record(
    db: AsyncSession,
    subscription: UserSubscription,
    user: User,
    purchase_token: str,
    order_id: str,
    transaction_time: datetime,
    dry_run: bool = False,
) -> SubscriptionTransaction:
    """创建交易记录"""
    import uuid

    # 从订阅计划获取价格信息
    amount = subscription.plan.price if subscription.plan else 0.0
    currency = subscription.plan.currency if subscription.plan else "USD"

    transaction_id = str(uuid.uuid4())
    transaction = SubscriptionTransaction(
        id=transaction_id,
        subscription_id=subscription.id,
        user_id=user.id,
        transaction_type=TransactionType.PURCHASE,
        amount=amount,
        currency=currency,
        google_play_purchase_token=purchase_token,
        google_play_order_id=order_id,
        status="COMPLETED",
        transaction_time=transaction_time,
        extra_data={
            "restored_manually": True,
            "restored_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    if dry_run:
        logger.info(f"[DRY RUN] 将创建交易记录:")
        logger.info(f"  - 交易ID: {transaction_id}")
        logger.info(f"  - 订阅ID: {subscription.id}")
        logger.info(f"  - 用户ID: {user.id}")
        logger.info(f"  - 类型: {TransactionType.PURCHASE}")
        logger.info(f"  - 金额: {amount} {currency}")
        logger.info(f"  - 状态: COMPLETED")
    else:
        db.add(transaction)
        logger.info(f"创建交易记录: {transaction.id}")

    return transaction


async def restore_subscription(dry_run: bool = False):
    """恢复用户订阅的主函数"""
    try:
        async with AsyncSessionLocal() as db:
            logger.info("=" * 60)
            if dry_run:
                logger.info(
                    "开始恢复用户订阅 [DRY RUN 模式 - 不会实际修改数据库]"
                )
            else:
                logger.info("开始恢复用户订阅")
            logger.info("=" * 60)

            # 1. 查找用户
            logger.info(f"查找用户: {USER_EMAIL}")
            user = await find_user_by_email(db, USER_EMAIL)
            logger.info(f"找到用户: {user.id} ({user.nickname or 'N/A'})")

            # 2. 查找订阅计划
            logger.info(f"查找订阅计划: {PLAN_ID}")
            plan = await find_subscription_plan(db, PLAN_ID)
            logger.info(
                f"找到订阅计划: {plan.name} (价格: {plan.price} {plan.currency})"
            )

            # 3. 检查是否已存在订阅记录
            logger.info("检查是否已存在订阅记录...")
            existing_subscription = await check_existing_subscription(
                db, PURCHASE_TOKEN, ORDER_ID
            )

            if existing_subscription:
                logger.warning(
                    f"订阅记录已存在: {existing_subscription.id}, 状态: {existing_subscription.status}"
                )
                logger.info("跳过创建，直接返回现有订阅")
                await db.refresh(existing_subscription)
                logger.info("=" * 60)
                logger.info("恢复完成（使用现有订阅）")
                logger.info("=" * 60)
                return existing_subscription

            # 4. 取消用户其他活跃订阅
            logger.info("检查并取消用户其他活跃订阅...")
            cancelled_count = await cancel_user_active_subscriptions(
                db, user.id, dry_run=dry_run
            )

            # 5. 创建订阅记录
            if dry_run:
                logger.info("[DRY RUN] 创建订阅记录...")
            else:
                logger.info("创建订阅记录...")
            subscription = await create_subscription_record(
                db,
                user,
                plan,
                PURCHASE_TOKEN,
                ORDER_ID,
                START_DATE,
                SUBSCRIPTION_DURATION_MONTHS,
                dry_run=dry_run,
            )

            # 6. 创建交易记录
            if dry_run:
                logger.info("[DRY RUN] 创建交易记录...")
            else:
                logger.info("创建交易记录...")
            transaction = await create_transaction_record(
                db,
                subscription,
                user,
                PURCHASE_TOKEN,
                ORDER_ID,
                START_DATE,
                dry_run=dry_run,
            )

            # 7. 在提交/回滚前先访问所有需要的属性值（避免回滚后无法访问）
            user_id = user.id
            user_email = user.email
            subscription_id = subscription.id
            plan_name = plan.name
            subscription_status = subscription.status
            start_date_str = (
                str(subscription.start_date)
                if subscription.start_date
                else "N/A"
            )
            end_date_str = (
                str(subscription.end_date) if subscription.end_date else "N/A"
            )
            auto_renew = subscription.auto_renew
            transaction_id = transaction.id

            # 8. 提交事务
            if dry_run:
                logger.info("[DRY RUN] 将提交事务（实际不会提交）")
                await db.rollback()  # 在 dry run 模式下回滚
            else:
                await db.commit()
                await db.refresh(subscription)

            logger.info("=" * 60)
            if dry_run:
                logger.info(
                    "订阅恢复校验完成！[DRY RUN 模式 - 未实际修改数据库]"
                )
            else:
                logger.info("订阅恢复成功！")
            logger.info("=" * 60)
            logger.info(f"用户ID: {user_id}")
            logger.info(f"用户邮箱: {user_email}")
            logger.info(f"订阅ID: {subscription_id}")
            logger.info(f"订阅计划: {plan_name}")
            logger.info(f"订阅状态: {subscription_status}")
            logger.info(f"开始时间: {start_date_str}")
            logger.info(f"结束时间: {end_date_str}")
            logger.info(f"自动续费: {auto_renew}")
            logger.info(f"购买令牌: {PURCHASE_TOKEN[:50]}...")
            logger.info(f"订单ID: {ORDER_ID}")
            logger.info(f"交易ID: {transaction_id}")
            if cancelled_count > 0:
                logger.info(f"已取消 {cancelled_count} 个其他活跃订阅")
            logger.info("=" * 60)

            return subscription

    except Exception as e:
        logger.error(f"恢复订阅失败: {str(e)}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="恢复用户订阅脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行 dry run 模式（校验，不实际修改）
  python restore_subscription.py --dry-run

  # 实际执行恢复操作
  python restore_subscription.py
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run 模式：只校验操作，不实际修改数据库",
    )

    args = parser.parse_args()

    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    # 运行恢复脚本
    asyncio.run(restore_subscription(dry_run=args.dry_run))
