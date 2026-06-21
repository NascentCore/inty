"""Subscription limits, purchases, and usage accounting.

TODO(commercialization-cleanup): Companion harness must not import this module; companion
WS billing entry points are ``chat_ws.py`` and ``inner_tick_fire.py`` only.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import Integer, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Environment, global_config_loaded_from_config_yaml
from app.api.core.user_privilege.superuser_check import (
    SUPERUSER_LIMIT_CHECK_RESULT,
    is_superuser,
)
from app.external_services.google_play_service import GooglePlayService
from app.models.subscription import (
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTransaction,
    SubscriptionUsage,
    TransactionType,
    UserSubscription,
)
from app.models.subscription_features import SubscriptionFeatures
from app.models.user import AuthType, User
from app.schemas.exclude_fields import EXCLUDE_FIELDS
from app.schemas.response import BusinessErrorCode
from app.schemas.subscription import (
    FeatureInfo,
    GooglePlayPurchaseRequest,
    PurchaseVerificationResponse,
)
from app.schemas.subscription import SubscriptionPlan as SubscriptionPlanSchema
from app.schemas.subscription import (
    SubscriptionPlanCreate,
    SubscriptionStatusResponse,
    UsageStatisticsResponse,
)
from app.schemas.subscription import UserSubscription as UserSubscriptionSchema
from app.services.system_settings_service import system_settings_service
from app.schemas.user import User as UserSchema

TEST_ENVIRONMENT_LIMIT = 1_000_000


class SubscriptionService:
    """订阅服务"""

    def __init__(self, google_play_service: GooglePlayService):
        """初始化订阅服务，使用注入方便测试"""
        self.google_play_service = google_play_service

    async def get_subscription_plans(
        self, db: AsyncSession, include_inactive: bool = False
    ) -> List[SubscriptionPlanSchema]:
        """获取订阅计划列表"""
        try:
            query = select(SubscriptionPlan)

            if not include_inactive:
                query = query.where(SubscriptionPlan.is_active == True)

            query = query.order_by(
                SubscriptionPlan.sort_order, SubscriptionPlan.created_at
            )

            result = await db.execute(query)
            plans = result.scalars().all()

            # 将 SQLAlchemy 模型转换为 Pydantic 模型
            return [
                SubscriptionPlanSchema.model_validate(plan) for plan in plans
            ]

        except Exception as e:
            logger.error(f"获取订阅计划列表失败: {str(e)}")
            raise

    async def get_subscription_plan(
        self, db: AsyncSession, plan_id: str
    ) -> Optional[SubscriptionPlanSchema]:
        """根据ID获取订阅计划"""
        try:
            result = await db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
            )
            plan = result.scalar_one_or_none()

            if plan:
                return SubscriptionPlanSchema.model_validate(plan)
            return None

        except Exception as e:
            logger.error(f"获取订阅计划失败: {str(e)}")
            raise

    async def get_subscription_plan_by_product_id(
        self, db: AsyncSession, product_id: str
    ) -> Optional[SubscriptionPlanSchema]:
        """根据Google Play产品ID获取订阅计划"""
        try:
            result = await db.execute(
                select(SubscriptionPlan).where(
                    SubscriptionPlan.google_play_product_id == product_id
                )
            )
            plan = result.scalar_one_or_none()

            if plan:
                return SubscriptionPlanSchema.model_validate(plan)
            return None

        except Exception as e:
            logger.error(f"根据产品ID获取订阅计划失败: {str(e)}")
            raise

    async def create_subscription_plan(
        self, db: AsyncSession, plan_data: SubscriptionPlanCreate
    ) -> SubscriptionPlan:
        """创建订阅计划"""
        try:
            # 排除数据库模型中不存在的字段
            plan_data_dict = plan_data.model_dump(exclude=EXCLUDE_FIELDS)
            plan = SubscriptionPlan(id=str(uuid.uuid4()), **plan_data_dict)

            db.add(plan)
            await db.commit()
            await db.refresh(plan)

            logger.info(f"创建订阅计划成功: {plan.id}")
            return plan

        except Exception as e:
            await db.rollback()
            logger.error(f"创建订阅计划失败: {str(e)}")
            raise

    async def has_ever_subscribed(self, db: AsyncSession, user_id: str) -> bool:
        """检查用户是否曾经有过订阅记录"""
        try:
            result = await db.execute(
                select(UserSubscription.id)
                .where(UserSubscription.user_id == user_id)
                .limit(1)
            )
            return result.first() is not None
        except Exception as e:
            logger.error(
                f"检查用户历史订阅记录失败: user_id={user_id}, error={str(e)}"
            )
            return False

    async def get_user_latest_plan_id(
        self, db: AsyncSession, user_id: str
    ) -> Optional[str]:
        """获取用户最新的订阅计划ID（Google Play Product ID）"""
        try:
            result = await db.execute(
                select(SubscriptionPlan.google_play_product_id)
                .select_from(UserSubscription)
                .join(SubscriptionPlan)
                .where(UserSubscription.user_id == user_id)
                .order_by(UserSubscription.created_at.desc())
                .limit(1)
            )
            product_id = result.scalar_one_or_none()
            return product_id
        except Exception as e:
            logger.error(
                f"获取用户最新订阅计划ID失败: user_id={user_id}, error={str(e)}"
            )
            return None

    async def get_user_current_subscription(
        self, db: AsyncSession, user_id: str
    ) -> Optional[UserSubscription]:
        """获取用户当前有效的订阅"""
        try:
            result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(
                    and_(
                        UserSubscription.user_id == user_id,
                        # 包含ACTIVE和CANCELLED状态，只要未到期就有效
                        UserSubscription.status.in_(
                            [
                                SubscriptionStatus.ACTIVE,
                                SubscriptionStatus.CANCELLED,
                            ]
                        ),
                        or_(
                            UserSubscription.end_date.is_(None),
                            UserSubscription.end_date
                            > datetime.now(timezone.utc),
                        ),
                    )
                )
                .order_by(UserSubscription.created_at.desc())
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取用户当前订阅失败: {str(e)}")
            raise

    async def get_user_subscription_status(
        self, db: AsyncSession, user_id: str
    ) -> SubscriptionStatusResponse:
        """获取用户订阅状态"""
        try:
            # 获取用户历史订阅记录
            has_ever_subscribed = await self.has_ever_subscribed(db, user_id)

            # 获取当前有效订阅
            subscription = await self.get_user_current_subscription(db, user_id)

            if subscription:
                remaining_days = None
                if subscription.end_date:
                    delta = subscription.end_date - datetime.now(timezone.utc)
                    remaining_days = max(0, delta.days)

                # 付费用户获得所有权益
                feature_list = []
                for (
                    feature_data
                ) in SubscriptionFeatures.get_premium_features_list():
                    feature_list.append(
                        FeatureInfo(
                            key=feature_data["key"],
                            name=feature_data["name"],
                            description=feature_data["description"],
                            type=feature_data["type"],
                            icon=feature_data["icon"],
                            order=feature_data["order"],
                            enabled=True,
                        )
                    )

                # 将 SQLAlchemy 模型转换为 Pydantic 模型
                subscription_schema = UserSubscriptionSchema.model_validate(
                    subscription
                )
                plan_schema = (
                    SubscriptionPlanSchema.model_validate(subscription.plan)
                    if subscription.plan
                    else None
                )

                # 判断订阅的详细状态
                subscription_status = "subscribed"
                will_auto_renew = subscription.auto_renew

                if subscription.status == SubscriptionStatus.CANCELLED:
                    subscription_status = (
                        "subscribed_expiring"  # 已取消但未到期
                    )
                    will_auto_renew = False
                elif subscription.auto_renew:
                    subscription_status = "subscribed"  # 正常订阅
                else:
                    subscription_status = (
                        "subscribed_expiring"  # 未取消但不自动续费
                    )

                return SubscriptionStatusResponse(
                    is_subscribed=True,
                    subscription_status=subscription_status,
                    has_ever_subscribed=has_ever_subscribed,
                    subscription=subscription_schema,
                    plan=plan_schema,
                    remaining_days=remaining_days,
                    will_auto_renew=will_auto_renew,
                    chat_limit_per_day=subscription.plan.chat_limit_per_day,
                    total_chat_limit=None,  # 付费用户不使用总次数限制
                    chat_24h_limit=None,  # 付费用户不使用24小时限制
                    guest_chat_24h_limit=None,  # 付费用户不需要游客限制
                    voice_24h_limit=global_config_loaded_from_config_yaml.app.limits.subscribed_user_voice_24h_limit,
                    guest_voice_24h_limit=None,  # 付费用户不需要游客限制
                    image_gen_24h_limit=global_config_loaded_from_config_yaml.app.limits.subscribed_user_image_gen_24h_limit,
                    agent_creation_24h_limit=global_config_loaded_from_config_yaml.app.limits.subscribed_user_agent_creation_24h_limit,
                    agent_creation_limit=subscription.plan.agent_creation_limit,
                    background_generation_limit_per_day=getattr(
                        subscription.plan,
                        "background_generation_limit_per_day",
                        -1,
                    ),
                    features=subscription.plan.features or {},
                    feature_list=feature_list,
                )
            else:
                # 免费用户的默认限制
                # 免费用户只启用真实权益，虚假权益显示但不启用
                feature_list = []
                for (
                    feature_data
                ) in SubscriptionFeatures.get_premium_features_list():
                    is_real_feature = SubscriptionFeatures.is_real_feature(
                        feature_data["key"]
                    )
                    feature_list.append(
                        FeatureInfo(
                            key=feature_data["key"],
                            name=feature_data["name"],
                            description=feature_data["description"],
                            type=feature_data["type"],
                            icon=feature_data["icon"],
                            order=feature_data["order"],
                            enabled=is_real_feature,  # 只有真实权益才启用
                        )
                    )

                # 从动态配置获取免费用户限制
                free_limits = (
                    await system_settings_service.get_free_user_limits(db)
                )

                return SubscriptionStatusResponse(
                    is_subscribed=False,
                    subscription_status="unsubscribed",
                    has_ever_subscribed=has_ever_subscribed,
                    subscription=None,
                    plan=None,
                    remaining_days=None,
                    will_auto_renew=False,
                    chat_limit_per_day=-1,  # 免费用户不限制每日聊天次数
                    total_chat_limit=free_limits["chat_total_limit"],
                    chat_24h_limit=free_limits["chat_24h_limit"],
                    guest_chat_24h_limit=free_limits["guest_chat_24h_limit"],
                    voice_24h_limit=free_limits["voice_24h_limit"],
                    guest_voice_24h_limit=free_limits["guest_voice_24h_limit"],
                    image_gen_24h_limit=free_limits["image_gen_24h_limit"],
                    agent_creation_24h_limit=free_limits[
                        "agent_creation_24h_limit"
                    ],
                    agent_creation_limit=free_limits["agent_creation_limit"],
                    background_generation_limit_per_day=free_limits[
                        "background_generation_limit"
                    ],
                    features={},
                    feature_list=feature_list,
                )

        except Exception as e:
            logger.error(f"获取用户订阅状态失败: {str(e)}")
            raise

    async def verify_and_create_subscription(
        self,
        db: AsyncSession,
        user_id: str,
        purchase_request: GooglePlayPurchaseRequest,
    ) -> PurchaseVerificationResponse:
        """验证购买并创建订阅"""
        try:
            # 查找对应的订阅计划
            plan = await self.get_subscription_plan_by_product_id(
                db, purchase_request.product_id
            )

            if not plan:
                return PurchaseVerificationResponse(
                    is_verified=False,
                    subscription=None,
                    message="Subscription plan not found",
                    error_code="PLAN_NOT_FOUND",
                )

            # 调用Google Play API验证购买
            is_valid, purchase_info = (
                self.google_play_service.verify_subscription_purchase(
                    purchase_request.product_id, purchase_request.purchase_token
                )
            )

            if not is_valid:
                return PurchaseVerificationResponse(
                    is_verified=False,
                    subscription=None,
                    message="Google Play purchase verification failed",
                    error_code="GOOGLE_PLAY_VERIFICATION_FAILED",
                )

            # 检查是否已经存在相同的购买令牌
            existing_subscription_result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(
                    UserSubscription.google_play_purchase_token
                    == purchase_request.purchase_token
                )
            )
            existing_subscription = (
                existing_subscription_result.scalar_one_or_none()
            )

            if existing_subscription:
                # 检查是否属于当前用户
                if existing_subscription.user_id == user_id:
                    # 属于当前用户，返回成功（webhook 可能已经创建了订阅记录）
                    logger.info(
                        f"订阅已存在，返回现有订阅记录 - 用户: {user_id}, 订阅: {existing_subscription.id}"
                    )
                    subscription_schema = UserSubscriptionSchema.model_validate(
                        existing_subscription
                    )
                    return PurchaseVerificationResponse(
                        is_verified=True,
                        subscription=subscription_schema,
                        message="Subscription already verified",
                    )
                else:
                    # 不属于当前用户，返回错误（安全考虑）
                    logger.warning(
                        f"购买令牌已被其他用户使用 - 当前用户: {user_id}, "
                        f"订阅用户: {existing_subscription.user_id}, "
                        f"购买令牌: {purchase_request.purchase_token[:10]}..."
                    )
                    return PurchaseVerificationResponse(
                        is_verified=False,
                        subscription=None,
                        message="Purchase token has already been used by another user",
                        error_code="DUPLICATE_PURCHASE_TOKEN_DIFFERENT_USER",
                    )

            # 检查用户是否有已取消但未到期的订阅
            current_subscription = await self.get_user_current_subscription(
                db, user_id
            )

            if (
                current_subscription
                and current_subscription.status == SubscriptionStatus.CANCELLED
            ):
                # 如果是重新订阅同一个计划，恢复现有订阅
                if current_subscription.plan_id == plan.id:
                    current_subscription.status = SubscriptionStatus.ACTIVE
                    current_subscription.auto_renew = True
                    current_subscription.google_play_purchase_token = (
                        purchase_request.purchase_token
                    )
                    current_subscription.google_play_order_id = (
                        purchase_request.order_id
                    )

                    # 更新订阅时间信息
                    if purchase_info.get("start_time"):
                        current_subscription.start_date = purchase_info.get(
                            "start_time"
                        )
                    if purchase_info.get("expiry_time"):
                        current_subscription.end_date = purchase_info.get(
                            "expiry_time"
                        )

                    # 更新元数据
                    extra_data = current_subscription.extra_data or {}
                    extra_data["resubscribed_at"] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    extra_data["google_play_info"] = (
                        self._make_json_serializable(purchase_info)
                    )
                    current_subscription.extra_data = extra_data

                    await db.commit()
                    await db.refresh(current_subscription)

                    logger.info(
                        f"恢复已取消的订阅 - 用户: {user_id}, 订阅: {current_subscription.id}"
                    )

                    # 重新查询订阅记录以确保关联对象被正确加载
                    result = await db.execute(
                        select(UserSubscription)
                        .options(selectinload(UserSubscription.plan))
                        .where(UserSubscription.id == current_subscription.id)
                    )
                    subscription = result.scalar_one()
                else:
                    # 不同计划，取消当前订阅，创建新订阅
                    await self._cancel_user_active_subscriptions(db, user_id)
                    subscription = None  # 标记需要创建新订阅
            else:
                # 取消用户当前的其他活跃订阅
                await self._cancel_user_active_subscriptions(db, user_id)
                subscription = None  # 标记需要创建新订阅

            # 如果需要创建新的订阅记录
            if subscription is None:
                start_date = purchase_info.get("start_time") or datetime.now(
                    timezone.utc
                )
                end_date = purchase_info.get("expiry_time")

                subscription = UserSubscription(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    plan_id=plan.id,
                    google_play_purchase_token=purchase_request.purchase_token,
                    google_play_order_id=purchase_request.order_id,
                    google_play_subscription_id=purchase_request.subscription_id,
                    status=SubscriptionStatus.ACTIVE,
                    start_date=start_date,
                    end_date=end_date,
                    auto_renew=purchase_info.get("auto_renewing", True),
                    extra_data={
                        "google_play_info": self._make_json_serializable(
                            purchase_info
                        )
                    },
                )

                db.add(subscription)

                # 创建交易记录
                transaction = SubscriptionTransaction(
                    id=str(uuid.uuid4()),
                    subscription_id=subscription.id,
                    user_id=user_id,
                    transaction_type=TransactionType.PURCHASE,
                    amount=self._safe_convert_price_micros(
                        purchase_info.get("price_amount_micros", 0)
                    ),  # 转换为实际金额
                    currency=purchase_info.get("price_currency_code", "USD"),
                    google_play_purchase_token=purchase_request.purchase_token,
                    google_play_order_id=purchase_request.order_id,
                    status="COMPLETED",
                    transaction_time=start_date,
                    extra_data={
                        "google_play_info": self._make_json_serializable(
                            purchase_info
                        )
                    },
                )

                db.add(transaction)

                await db.commit()
                await db.refresh(subscription)

                # 重新查询订阅记录以确保关联对象被正确加载
                result = await db.execute(
                    select(UserSubscription)
                    .options(selectinload(UserSubscription.plan))
                    .where(UserSubscription.id == subscription.id)
                )
                subscription = result.scalar_one()

                logger.info(
                    f"新订阅创建成功 - 用户: {user_id}, 订阅: {subscription.id}"
                )

            # 确认购买（向Google Play发送确认）
            self.google_play_service.acknowledge_subscription(
                purchase_request.product_id, purchase_request.purchase_token
            )

            # 将 SQLAlchemy 模型转换为 Pydantic 模型
            subscription_schema = UserSubscriptionSchema.model_validate(
                subscription
            )

            return PurchaseVerificationResponse(
                is_verified=True,
                subscription=subscription_schema,
                message="Subscription verified successfully",
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"验证购买并创建订阅失败: {str(e)}")
            return PurchaseVerificationResponse(
                is_verified=False,
                subscription=None,
                message="Internal server error",
                error_code="INTERNAL_ERROR",
            )

    async def _cancel_user_active_subscriptions(
        self, db: AsyncSession, user_id: str
    ) -> None:
        """取消用户当前的所有活跃订阅"""
        try:
            # 查询用户的所有活跃订阅
            result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(
                    and_(
                        UserSubscription.user_id == user_id,
                        UserSubscription.status == SubscriptionStatus.ACTIVE,
                    )
                )
            )

            active_subscriptions = result.scalars().all()

            for subscription in active_subscriptions:
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.auto_renew = False

                # 尝试在Google Play端取消订阅
                try:
                    if (
                        subscription.google_play_purchase_token
                        and subscription.plan
                    ):
                        self.google_play_service.cancel_subscription(
                            subscription.plan.google_play_product_id,
                            subscription.google_play_purchase_token,
                        )
                        logger.info(
                            f"已在Google Play端取消订阅: {subscription.id}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Google Play端取消订阅失败: {subscription.id}, 错误: {str(e)}"
                    )
                    # 即使Google Play端取消失败，也继续本地取消

            if active_subscriptions:
                logger.info(
                    f"取消用户 {user_id} 的 {len(active_subscriptions)} 个活跃订阅"
                )

        except Exception as e:
            logger.error(f"取消用户活跃订阅失败: {str(e)}")
            raise

    async def cancel_user_subscriptions_for_deletion(
        self, db: AsyncSession, user_id: str
    ) -> dict:
        """
        为账户删除取消用户订阅

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            dict: 取消结果统计
        """
        try:
            # 查询用户的所有活跃订阅
            result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(
                    and_(
                        UserSubscription.user_id == user_id,
                        UserSubscription.status == SubscriptionStatus.ACTIVE,
                    )
                )
            )

            active_subscriptions = result.scalars().all()

            cancellation_stats = {
                "subscriptions_cancelled": 0,
                "google_play_cancelled": 0,
                "local_only_cancelled": 0,
            }

            for subscription in active_subscriptions:
                # 更新本地订阅状态
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.auto_renew = False

                # 在额外数据中标记为用户删除导致的取消
                extra_data = subscription.extra_data or {}
                extra_data["cancelled_for_account_deletion"] = {
                    "cancelled_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "user_account_deletion",
                }
                subscription.extra_data = self._make_json_serializable(
                    extra_data
                )

                cancellation_stats["subscriptions_cancelled"] += 1

                # 尝试在Google Play端取消订阅
                google_play_success = False
                try:
                    if (
                        subscription.google_play_purchase_token
                        and subscription.plan
                    ):
                        self.google_play_service.cancel_subscription(
                            subscription.plan.google_play_product_id,
                            subscription.google_play_purchase_token,
                        )
                        google_play_success = True
                        cancellation_stats["google_play_cancelled"] += 1
                        logger.info(
                            f"Google Play端取消订阅成功: {subscription.id}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Google Play端取消订阅失败: {subscription.id}, 错误: {str(e)}"
                    )

                if not google_play_success:
                    cancellation_stats["local_only_cancelled"] += 1

                # 创建取消交易记录
                try:
                    await self._create_cancellation_transaction(
                        db, subscription, "account_deletion"
                    )
                except Exception as e:
                    logger.warning(
                        f"创建取消交易记录失败: {subscription.id}, 错误: {str(e)}"
                    )

            await db.commit()

            logger.info(
                f"用户 {user_id} 订阅取消完成，统计: {cancellation_stats}"
            )

            return cancellation_stats

        except Exception as e:
            await db.rollback()
            logger.error(f"为账户删除取消用户订阅失败: {str(e)}")
            raise

    async def _create_cancellation_transaction(
        self,
        db: AsyncSession,
        subscription: UserSubscription,
        reason: str = "user_requested",
    ) -> None:
        """创建取消交易记录"""
        try:
            transaction = SubscriptionTransaction(
                id=str(uuid.uuid4()),
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                transaction_type=TransactionType.CANCEL,
                amount=0.0,  # 取消不涉及金额
                currency=(
                    subscription.plan.currency if subscription.plan else "USD"
                ),
                google_play_purchase_token=subscription.google_play_purchase_token,
                google_play_order_id=subscription.google_play_order_id,
                status="COMPLETED",
                transaction_time=datetime.now(timezone.utc),
                extra_data={"cancellation_reason": reason},
            )

            db.add(transaction)
            logger.debug(
                f"创建取消交易记录成功 - 订阅: {subscription.id}, 原因: {reason}"
            )

        except Exception as e:
            logger.error(f"创建取消交易记录失败: {str(e)}")
            raise

    async def record_usage(
        self,
        db: Optional[AsyncSession],
        user_id: str,
        usage_type: str,
        usage_count: int = 1,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[SubscriptionUsage]:
        """记录用户使用情况"""
        from app.api.deps import get_async_db

        # 优先复用调用方会话；若该会话已处于异常事务状态，则自动降级到独立会话重试一次。
        if db is not None:
            usage = await self._record_usage_impl(
                db, user_id, usage_type, usage_count, extra_data
            )
            if usage is not None:
                return usage
            logger.warning(
                "记录用户用量失败，改用独立数据库会话重试: "
                f"user_id={user_id}, usage_type={usage_type}"
            )

        async for db_session in get_async_db():
            return await self._record_usage_impl(
                db_session, user_id, usage_type, usage_count, extra_data
            )
        return None

    async def _record_usage_impl(
        self,
        db: AsyncSession,
        user_id: str,
        usage_type: str,
        usage_count: int = 1,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[SubscriptionUsage]:
        """实际的记录使用情况实现"""
        try:
            # 获取用户当前订阅
            subscription = await self.get_user_current_subscription(db, user_id)

            usage = SubscriptionUsage(
                id=str(uuid.uuid4()),
                user_id=user_id,
                subscription_id=subscription.id if subscription else None,
                usage_type=usage_type,
                usage_date=datetime.now(timezone.utc),
                usage_count=usage_count,
                extra_data=extra_data or {},
            )

            db.add(usage)
            await db.commit()
            await db.refresh(usage)

            return usage

        except Exception:
            logger.exception(
                "记录用户使用情况失败: user_id={}, usage_type={}",
                user_id,
                usage_type,
            )
            try:
                await db.rollback()
            except Exception:
                logger.exception(
                    "记录用户使用情况失败后的数据库回滚失败: user_id={}, usage_type={}",
                    user_id,
                    usage_type,
                )
            return None  # 返回None而不是抛异常，避免影响主流程

    async def get_user_usage_statistics(
        self, db: AsyncSession, user_id: str
    ) -> UsageStatisticsResponse:
        """获取用户使用统计"""
        try:
            # 获取订阅状态
            subscription_status = await self.get_user_subscription_status(
                db, user_id
            )

            # 获取今日聊天次数
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time()).replace(
                tzinfo=timezone.utc
            )
            today_end = today_start + timedelta(days=1)

            chat_count_result = await db.execute(
                select(func.sum(SubscriptionUsage.usage_count)).where(
                    and_(
                        SubscriptionUsage.user_id == user_id,
                        SubscriptionUsage.usage_type == "chat",
                        SubscriptionUsage.usage_date >= today_start,
                        SubscriptionUsage.usage_date < today_end,
                    )
                )
            )
            today_chat_count = chat_count_result.scalar() or 0

            # 获取用户总聊天次数（免费用户需要）
            total_chat_count = None
            if subscription_status.total_chat_limit is not None:
                total_chat_count_result = await db.execute(
                    select(func.sum(SubscriptionUsage.usage_count)).where(
                        and_(
                            SubscriptionUsage.user_id == user_id,
                            SubscriptionUsage.usage_type == "chat",
                        )
                    )
                )
                total_chat_count = total_chat_count_result.scalar() or 0

            # 获取用户24小时内聊天次数（免费用户需要）
            chat_24h_count = None
            if subscription_status.chat_24h_limit is not None:
                now = datetime.now(timezone.utc)
                hours_24_ago = now - timedelta(hours=24)

                chat_24h_count_result = await db.execute(
                    select(func.sum(SubscriptionUsage.usage_count)).where(
                        and_(
                            SubscriptionUsage.user_id == user_id,
                            SubscriptionUsage.usage_type == "chat",
                            SubscriptionUsage.usage_date >= hours_24_ago,
                        )
                    )
                )
                chat_24h_count = chat_24h_count_result.scalar() or 0

            # 获取用户创建的Agent数量
            from app.models.agent import Agent

            agent_count_result = await db.execute(
                select(func.count(Agent.id)).where(
                    and_(
                        Agent.creator_id == user_id, Agent.deleted_at.is_(None)
                    )
                )
            )
            agent_count = agent_count_result.scalar() or 0

            # 获取最近的使用历史
            usage_result = await db.execute(
                select(SubscriptionUsage)
                .where(SubscriptionUsage.user_id == user_id)
                .order_by(SubscriptionUsage.created_at.desc())
                .limit(10)
            )
            usage_history = usage_result.scalars().all()

            # 将 SQLAlchemy 模型转换为 Pydantic 模型
            from app.schemas.subscription import (
                SubscriptionUsage as SubscriptionUsageSchema,
            )

            usage_history_schemas = [
                SubscriptionUsageSchema.model_validate(usage)
                for usage in usage_history
            ]

            return UsageStatisticsResponse(
                today_chat_count=today_chat_count,
                today_limit=subscription_status.chat_limit_per_day,
                total_chat_count=total_chat_count,
                total_chat_limit=subscription_status.total_chat_limit,
                chat_24h_count=chat_24h_count,
                chat_24h_limit=subscription_status.chat_24h_limit,
                agent_count=agent_count,
                agent_limit=subscription_status.agent_creation_limit,
                usage_history=usage_history_schemas,
            )

        except Exception as e:
            logger.error(f"获取用户使用统计失败: {str(e)}")
            raise

    async def check_chat_limit(
        self, db: AsyncSession, user: UserSchema
    ) -> Tuple[bool, int, int]:
        """
        检查用户聊天次数限制

        Returns:
            Tuple[bool, int, int]: (是否允许聊天, 已用次数, 限制次数)
        """
        try:
            # Opt-in for isolated test subprocesses only (see tests/companion_ws_bootstrap/server.py).
            if os.environ.get("INTY_E2E_RELAX_SUBSCRIPTION") == "1":
                return True, 0, TEST_ENVIRONMENT_LIMIT
            if (
                global_config_loaded_from_config_yaml.app.environment
                == Environment.TEST
                and not global_config_loaded_from_config_yaml.app.debug
            ):
                logger.debug("TEST 环境下放宽聊天限额: user_id=%s", user.id)
                return True, 0, TEST_ENVIRONMENT_LIMIT

            if is_superuser(user):
                logger.debug(f"Superuser {user.id} has unlimited chats")
                return SUPERUSER_LIMIT_CHECK_RESULT

            # 获取订阅状态
            subscription_status = await self.get_user_subscription_status(
                db, user.id
            )

            # 免费用户：检查24小时聊天次数限制
            if subscription_status.chat_24h_limit is not None:
                # 如果是游客用户，使用游客限制；否则使用普通免费用户限制
                if user.auth_type == AuthType.GUEST:
                    chat_limit = subscription_status.guest_chat_24h_limit
                else:
                    chat_limit = subscription_status.chat_24h_limit
            elif not subscription_status.is_subscribed:
                # 回退配置：根据用户类型使用不同的限制
                if user.auth_type == AuthType.GUEST:
                    chat_limit = (
                        global_config_loaded_from_config_yaml.app.limits.guest_user_chat_24h_limit
                    )
                else:
                    chat_limit = (
                        global_config_loaded_from_config_yaml.app.limits.free_user_chat_24h_limit
                    )
            else:
                chat_limit = None

            if chat_limit is not None:
                # 获取过去24小时内的聊天次数
                now = datetime.now(timezone.utc)
                hours_24_ago = now - timedelta(hours=24)

                chat_24h_count_result = await db.execute(
                    select(func.sum(SubscriptionUsage.usage_count)).where(
                        and_(
                            SubscriptionUsage.user_id == user.id,
                            SubscriptionUsage.usage_type == "chat",
                            SubscriptionUsage.usage_date >= hours_24_ago,
                        )
                    )
                )
                chat_24h_count = chat_24h_count_result.scalar() or 0

                # 检查是否超出24小时限制
                is_allowed = chat_24h_count < chat_limit

                return (
                    is_allowed,
                    chat_24h_count,
                    chat_limit,
                )

            # 付费用户：检查每日聊天次数限制
            # 如果是无限制，直接返回允许
            if subscription_status.chat_limit_per_day == -1:
                return True, 0, -1

            # 获取今日聊天次数
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time()).replace(
                tzinfo=timezone.utc
            )
            today_end = today_start + timedelta(days=1)

            chat_count_result = await db.execute(
                select(func.sum(SubscriptionUsage.usage_count)).where(
                    and_(
                        SubscriptionUsage.user_id == user.id,
                        SubscriptionUsage.usage_type == "chat",
                        SubscriptionUsage.usage_date >= today_start,
                        SubscriptionUsage.usage_date < today_end,
                    )
                )
            )
            today_chat_count = chat_count_result.scalar() or 0

            # 检查是否超出限制
            is_allowed = (
                today_chat_count < subscription_status.chat_limit_per_day
            )

            return (
                is_allowed,
                today_chat_count,
                subscription_status.chat_limit_per_day,
            )

        except Exception as e:
            logger.error(f"检查聊天次数限制失败: {str(e)}")
            # 出错时默认允许，避免影响用户体验
            return True, 0, -1

    async def check_voice_generation_limit(
        self, db: AsyncSession, user: UserSchema
    ) -> Tuple[bool, int, int]:
        """
        检查用户语音生成次数限制

        Returns:
            Tuple[bool, int, int]: (是否允许生成, 已用次数, 限制次数)
        """
        try:
            if (
                global_config_loaded_from_config_yaml.app.environment
                == Environment.TEST
                and not global_config_loaded_from_config_yaml.app.debug
            ):
                logger.debug("TEST 环境下放宽语音生成限额: user_id=%s", user.id)
                return True, 0, TEST_ENVIRONMENT_LIMIT

            if is_superuser(user):
                logger.debug(
                    f"Superuser {user.id} has unlimited voice generation"
                )
                return SUPERUSER_LIMIT_CHECK_RESULT

            # 获取订阅状态
            subscription_status = await self.get_user_subscription_status(
                db, user.id
            )

            # 确定语音生成限制
            if subscription_status.is_subscribed:
                # 付费用户使用订阅限制
                voice_limit = subscription_status.voice_24h_limit
            else:
                # 免费用户根据类型使用不同限制
                if user.auth_type == AuthType.GUEST:
                    voice_limit = subscription_status.guest_voice_24h_limit
                else:
                    voice_limit = subscription_status.voice_24h_limit

            if voice_limit is None:
                # 如果没有限制，返回允许
                return True, 0, -1

            # 获取过去24小时内的语音生成次数
            now = datetime.now(timezone.utc)
            hours_24_ago = now - timedelta(hours=24)

            voice_count_result = await db.execute(
                select(func.sum(SubscriptionUsage.usage_count)).where(
                    and_(
                        SubscriptionUsage.user_id == user.id,
                        SubscriptionUsage.usage_type == "voice_generation",
                        SubscriptionUsage.usage_date >= hours_24_ago,
                    )
                )
            )
            voice_24h_count = voice_count_result.scalar() or 0

            # 检查是否超出限制
            is_allowed = voice_24h_count < voice_limit

            return is_allowed, voice_24h_count, voice_limit

        except Exception as e:
            logger.error(f"检查语音生成次数限制失败: {str(e)}")
            # 出错时默认允许，避免影响用户体验
            return True, 0, -1

    async def check_agent_creation_limit(
        self, db: AsyncSession, user: UserSchema
    ) -> Tuple[bool, int, int]:
        """
        检查用户Agent创建数量限制（24小时滚动窗口）

        Returns:
            Tuple[bool, int, int]: (是否允许创建, 已创建数量, 限制数量)
        """
        try:
            if (
                global_config_loaded_from_config_yaml.app.environment
                == Environment.TEST
                and not global_config_loaded_from_config_yaml.app.debug
            ):
                logger.debug(
                    "TEST 环境下放宽 Agent 创建限额: user_id=%s", user.id
                )
                return True, 0, TEST_ENVIRONMENT_LIMIT

            if is_superuser(user):
                return SUPERUSER_LIMIT_CHECK_RESULT

            # 获取订阅状态
            subscription_status = await self.get_user_subscription_status(
                db, user.id
            )

            # 确定Agent创建限制
            if subscription_status.is_subscribed:
                # 付费用户使用订阅限制
                agent_limit = (
                    global_config_loaded_from_config_yaml.app.limits.subscribed_user_agent_creation_24h_limit
                )
            else:
                # 免费用户使用免费限制
                agent_limit = (
                    global_config_loaded_from_config_yaml.app.limits.free_user_agent_creation_24h_limit
                )

            if agent_limit is None:
                # 如果没有限制，返回允许
                return True, 0, -1

            # 获取过去24小时内创建的Agent数量
            from app.models.agent import Agent

            now = datetime.now(timezone.utc)
            hours_24_ago = now - timedelta(hours=24)

            agent_count_result = await db.execute(
                select(func.count(Agent.id)).where(
                    and_(
                        Agent.creator_id == user.id,
                        Agent.created_at >= hours_24_ago,
                        Agent.deleted_at.is_(None),
                    )
                )
            )
            agent_24h_count = agent_count_result.scalar() or 0

            # 检查是否超出限制
            is_allowed = agent_24h_count < agent_limit

            return is_allowed, agent_24h_count, agent_limit

        except Exception as e:
            logger.error(f"检查Agent创建数量限制失败: {str(e)}")
            # 出错时默认允许，避免影响用户体验
            return True, 0, -1

    async def check_image_gen_limit(
        self, db: AsyncSession, user: UserSchema
    ) -> Tuple[bool, int, int]:
        """
        检查用户图片生成次数限制（24小时滚动窗口）

        Returns:
            Tuple[bool, int, int]: (是否允许生成, 已用次数, 限制次数)
        """
        try:
            if (
                global_config_loaded_from_config_yaml.app.environment
                == Environment.TEST
                and not global_config_loaded_from_config_yaml.app.debug
            ):
                logger.debug("TEST 环境下放宽图片生成限额: user_id=%s", user.id)
                return True, 0, TEST_ENVIRONMENT_LIMIT

            if is_superuser(user):
                logger.debug(
                    f"Superuser {user.id} has unlimited image generation"
                )
                return SUPERUSER_LIMIT_CHECK_RESULT

            # 游客用户不允许生成图片
            if user.auth_type == AuthType.GUEST:
                logger.debug(
                    f"Guest user {user.id} is not allowed to generate images"
                )
                return False, 0, 0

            # 获取订阅状态
            subscription_status = await self.get_user_subscription_status(
                db, user.id
            )

            # 确定图片生成限制
            if subscription_status.is_subscribed:
                # 付费用户使用订阅限制
                image_limit = (
                    global_config_loaded_from_config_yaml.app.limits.subscribed_user_image_gen_24h_limit
                )
            else:
                # 免费用户使用免费限制
                image_limit = (
                    global_config_loaded_from_config_yaml.app.limits.free_user_image_gen_24h_limit
                )

            if image_limit is None:
                # 如果没有限制，返回允许
                return True, 0, -1

            # 获取过去24小时内的图片生成次数
            # 统计所有图片生成类型：background_generation（背景图生成）和 image_generation（聊天图片生成）
            now = datetime.now(timezone.utc)
            hours_24_ago = now - timedelta(hours=24)

            generation_count_result = await db.execute(
                select(func.sum(SubscriptionUsage.usage_count)).where(
                    and_(
                        SubscriptionUsage.user_id == user.id,
                        SubscriptionUsage.usage_type.in_(
                            ["background_generation", "image_generation"]
                        ),
                        SubscriptionUsage.usage_date >= hours_24_ago,
                    )
                )
            )
            image_24h_count = generation_count_result.scalar() or 0

            # 检查是否超出限制
            is_allowed = image_24h_count < image_limit

            return is_allowed, image_24h_count, image_limit

        except Exception as e:
            logger.error(f"检查图片生成次数限制失败: {str(e)}")
            # 出错时默认允许，避免影响用户体验
            return True, 0, -1

    async def check_music_gen_limit(
        self, db: AsyncSession, user: UserSchema
    ) -> Tuple[bool, int, int]:
        """
        检查用户音乐生成次数限制（24小时滚动窗口）

        Returns:
            Tuple[bool, int, int]: (是否允许生成, 已用次数, 限制次数)
        """
        try:
            if (
                global_config_loaded_from_config_yaml.app.environment
                == Environment.TEST
                and not global_config_loaded_from_config_yaml.app.debug
            ):
                logger.debug("TEST 环境下放宽音乐生成限额: user_id=%s", user.id)
                return True, 0, TEST_ENVIRONMENT_LIMIT

            if is_superuser(user):
                logger.debug(
                    f"Superuser {user.id} has unlimited music generation"
                )
                return SUPERUSER_LIMIT_CHECK_RESULT

            # 游客用户不允许生成音乐
            if user.auth_type == AuthType.GUEST:
                logger.debug(
                    f"Guest user {user.id} is not allowed to generate music"
                )
                return False, 0, 0

            subscription_status = await self.get_user_subscription_status(
                db, user.id
            )
            if subscription_status.is_subscribed:
                music_limit = (
                    global_config_loaded_from_config_yaml.app.limits.subscribed_user_music_gen_24h_limit
                )
            else:
                music_limit = (
                    global_config_loaded_from_config_yaml.app.limits.free_user_music_gen_24h_limit
                )

            if music_limit is None:
                return True, 0, -1

            now = datetime.now(timezone.utc)
            hours_24_ago = now - timedelta(hours=24)
            generation_count_result = await db.execute(
                select(func.sum(SubscriptionUsage.usage_count)).where(
                    and_(
                        SubscriptionUsage.user_id == user.id,
                        SubscriptionUsage.usage_type == "music_generation",
                        SubscriptionUsage.usage_date >= hours_24_ago,
                    )
                )
            )
            music_24h_count = generation_count_result.scalar() or 0
            is_allowed = music_24h_count < music_limit
            return is_allowed, music_24h_count, music_limit
        except Exception as e:
            logger.error(f"检查音乐生成次数限制失败: {str(e)}")
            return True, 0, -1

    async def check_live_chat_limit(
        self, db: AsyncSession, user: UserSchema, agent_id: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检查用户 Live Chat 用量限制

        检查三项限制：
        1. 累计可聊天的 agent 数量
        2. 24 小时内与目标 agent 的通话时长
        3. 24 小时内跨所有 agent 的总通话时长

        Args:
            db: 数据库会话
            user: 用户对象
            agent_id: 目标 Agent ID

        Returns:
            Tuple[bool, str, Dict]: (是否允许, 拒绝原因, 详细信息)
            - 允许时: (True, "", {})
            - 拒绝时: (False, "reason_code", {"detail": ...})
        """
        try:
            gemini_live_config = (
                global_config_loaded_from_config_yaml.gemini_live
            )

            is_superuser_flag = is_superuser(user)
            if is_superuser_flag:
                logger.debug(f"Superuser {user.id}: 不限制 24h 总时长")

            subscription_status = await self.get_user_subscription_status(
                db, user.id
            )
            is_subscribed = (
                subscription_status.is_subscribed or is_superuser_flag
            )

            if is_subscribed:
                agent_limit = gemini_live_config.sub_user_agent_limit
                max_session_duration = (
                    gemini_live_config.sub_user_max_session_duration
                )
                total_duration_limit = (
                    gemini_live_config.sub_user_total_duration_24h
                )
            else:
                agent_limit = gemini_live_config.free_user_agent_limit
                max_session_duration = (
                    gemini_live_config.free_user_max_session_duration
                )
                total_duration_limit = (
                    gemini_live_config.free_user_total_duration_24h
                )

            # 使用 ->> 操作符提取 JSON 字段为文本（兼容 JSON 和 JSONB 类型）
            distinct_agents_result = await db.execute(
                select(SubscriptionUsage.extra_data.op("->>")("agent_id"))
                .where(
                    and_(
                        SubscriptionUsage.user_id == user.id,
                        SubscriptionUsage.usage_type == "live_chat",
                    )
                )
                .distinct()
            )
            chatted_agents = [
                row[0] for row in distinct_agents_result.fetchall() if row[0]
            ]
            chatted_agent_count = len(chatted_agents)

            is_new_agent = agent_id not in chatted_agents

            # Superuser 不检查 agent 数量限制
            if (
                not is_superuser_flag
                and is_new_agent
                and chatted_agent_count >= agent_limit
            ):
                logger.info(
                    f"用户 {user.id} Live Chat agent 数量已达上限: "
                    f"{chatted_agent_count}/{agent_limit}"
                )
                if subscription_status.is_subscribed:
                    error_info = BusinessErrorCode.LIVE_CHAT_AGENT_LIMIT_REACHED
                else:
                    error_info = BusinessErrorCode.SUBSCRIPTION_REQUIRED
                return (
                    False,
                    error_info["error_code"],
                    {
                        "used_count": chatted_agent_count,
                        "limit": agent_limit,
                        "is_subscribed": is_subscribed,
                        "error_info": error_info,
                    },
                )

            now = datetime.now(timezone.utc)
            hours_24_ago = now - timedelta(hours=24)

            # 检查 24h 内跨所有 agent 的总时长
            total_duration_result = await db.execute(
                select(
                    func.coalesce(
                        func.sum(
                            func.cast(
                                SubscriptionUsage.extra_data.op("->>")(
                                    "duration_seconds"
                                ),
                                Integer,
                            )
                        ),
                        0,
                    )
                ).where(
                    and_(
                        SubscriptionUsage.user_id == user.id,
                        SubscriptionUsage.usage_type == "live_chat",
                        SubscriptionUsage.usage_date >= hours_24_ago,
                    )
                )
            )
            total_used_duration = total_duration_result.scalar() or 0

            # Superuser 不检查 24h 总时长限制
            if (
                not is_superuser_flag
                and total_used_duration >= total_duration_limit
            ):
                logger.info(
                    f"用户 {user.id} 的 24h Live Chat 总时长已达上限: "
                    f"{total_used_duration}/{total_duration_limit}s"
                )
                if subscription_status.is_subscribed:
                    error_info = (
                        BusinessErrorCode.LIVE_CHAT_DURATION_LIMIT_REACHED
                    )
                else:
                    error_info = BusinessErrorCode.SUBSCRIPTION_REQUIRED
                return (
                    False,
                    error_info["error_code"],
                    {
                        "used_duration": total_used_duration,
                        "limit": total_duration_limit,
                        "is_subscribed": is_subscribed,
                        "error_info": error_info,
                    },
                )

            # Superuser 不限制时长
            if is_superuser_flag:
                remaining_duration = 86400  # 24 小时，实际不限制
            else:
                remaining_total = max(
                    0, total_duration_limit - total_used_duration
                )
                remaining_duration = min(max_session_duration, remaining_total)
            logger.info(
                f"Live Chat 限制检查 - user_id: {user.id}, agent_id: {agent_id}, "
                f"max_session_duration: {max_session_duration}s, "
                f"total_used: {total_used_duration}s, total_limit: {total_duration_limit}s, "
                f"remaining: {remaining_duration}s, is_subscribed: {is_subscribed}, "
                f"is_superuser: {is_superuser_flag}"
            )
            return (
                True,
                "",
                {
                    "remaining_duration": remaining_duration,
                    "agent_count": chatted_agent_count,
                    "agent_limit": agent_limit,
                    "is_new_agent": is_new_agent,
                },
            )

        except Exception as e:
            logger.error(f"检查 Live Chat 限制失败: {str(e)}")
            return True, "", {}

    async def handle_subscription_notification(
        self, db: AsyncSession, notification_data: Dict[str, Any]
    ) -> bool:
        """处理Google Play订阅状态变化通知"""
        try:
            # 首先检查是否是退款通知
            refund_handled = await self.process_google_play_refund_notification(
                db, notification_data
            )
            if refund_handled:
                return True

            subscription_notification = notification_data.get(
                "subscriptionNotification"
            )
            if not subscription_notification:
                return False

            purchase_token = subscription_notification.get("purchaseToken")
            notification_type = subscription_notification.get(
                "notificationType"
            )

            logger.info(
                f"处理订阅通知: {subscription_notification}, notification_type: {notification_type}"
            )

            if not purchase_token:
                return False

            # 查找对应的订阅记录
            result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(
                    UserSubscription.google_play_purchase_token
                    == purchase_token
                )
            )
            subscription = result.scalar_one_or_none()

            if not subscription:
                # 尝试自动创建订阅记录
                subscription = (
                    await self._try_create_subscription_from_notification(
                        db, purchase_token, notification_type, notification_data
                    )
                )

                if not subscription:
                    # 对于类型4 (SUBSCRIPTION_PURCHASED)，如果无法创建订阅记录（无法推断用户ID），
                    # 这是正常情况，由 app 端 verify 接口创建订阅记录
                    if notification_type == 4:
                        logger.info(
                            f"首次购买通知 (类型4) - 购买令牌: {purchase_token[:10]}...，"
                            f"无法推断用户ID，等待 app 端 verify 接口创建订阅记录"
                        )
                        return True

                    # 对于其他类型（续费、恢复），无法创建订阅记录是错误情况
                    logger.warning(
                        f"未找到对应的订阅记录且无法创建: {purchase_token}, 通知类型: {notification_type}"
                    )
                    logger.error(
                        f"无法为购买令牌创建订阅记录: {purchase_token}"
                    )
                    return False

                logger.info(f"成功从RTDN通知创建订阅记录: {subscription.id}")

            # 根据通知类型更新订阅状态
            await self._update_subscription_by_notification_type(
                db, subscription, notification_type, notification_data
            )

            return True

        except Exception as e:
            logger.error(f"处理订阅通知失败: {str(e)}")
            return False

    async def _try_create_subscription_from_notification(
        self,
        db: AsyncSession,
        purchase_token: str,
        notification_type: int,
        notification_data: Dict[str, Any],
    ) -> Optional[UserSubscription]:
        """
        尝试从RTDN通知创建订阅记录

        Args:
            db: 数据库会话
            purchase_token: 购买令牌
            notification_type: 通知类型
            notification_data: 通知数据

        Returns:
            Optional[UserSubscription]: 创建的订阅记录或None
        """
        try:
            # 只在特定通知类型下尝试创建订阅记录
            # 1: SUBSCRIPTION_RECOVERED, 2: SUBSCRIPTION_RENEWED, 4: SUBSCRIPTION_PURCHASED
            # 对于类型4，如果能够推断用户ID（通过 ObfuscatedAccountId），则可以创建订阅记录
            if notification_type not in [1, 2, 4]:
                logger.debug(f"通知类型 {notification_type} 不适合创建订阅记录")
                return None

            # 从通知数据中尝试提取产品ID（用于日志记录）
            subscription_notification = notification_data.get(
                "subscriptionNotification", {}
            )
            logger.debug(f"处理订阅通知: {subscription_notification}")

            # 获取所有订阅计划以匹配产品ID
            plans = await self.get_subscription_plans(db, include_inactive=True)

            subscription_created = None

            # 遍历所有订阅计划，尝试验证购买
            for plan in plans:
                try:
                    # 使用Google Play API验证购买
                    is_valid, purchase_info = (
                        self.google_play_service.verify_subscription_purchase(
                            plan.google_play_product_id, purchase_token
                        )
                    )

                    if is_valid and "error" not in purchase_info:
                        logger.debug(
                            f"找到匹配的订阅计划: {plan.id}, 产品ID: {plan.google_play_product_id}"
                        )

                        # 尝试从购买信息中推断用户ID
                        user_id = await self._infer_user_id_from_purchase_info(
                            db, purchase_info
                        )

                        if not user_id:
                            logger.warning(
                                f"无法从购买信息中推断用户ID: {purchase_token}"
                            )
                            continue

                        # 创建订阅记录
                        subscription_created = (
                            await self._create_subscription_from_purchase_info(
                                db,
                                user_id,
                                plan,
                                purchase_token,
                                purchase_info,
                                notification_data,
                            )
                        )

                        if subscription_created:
                            logger.info(
                                f"成功创建订阅记录: {subscription_created.id}"
                            )
                            break

                except Exception as e:
                    logger.debug(f"验证计划 {plan.id} 失败: {str(e)}")
                    continue

            return subscription_created

        except Exception as e:
            logger.error(f"从通知创建订阅记录失败: {str(e)}")
            return None

    async def _infer_user_id_from_purchase_info(
        self, db: AsyncSession, purchase_info: Dict[str, Any]
    ) -> Optional[str]:
        """
        从购买信息中推断用户ID

        Args:
            db: 数据库会话
            purchase_info: 购买信息

        Returns:
            Optional[str]: 用户ID或None
        """
        try:
            # 尝试从购买信息中获取用户标识
            obfuscated_account_id = purchase_info.get(
                "obfuscated_external_account_id"
            )
            email_address = purchase_info.get("email_address")
            profile_id = purchase_info.get("profile_id")
            order_id = purchase_info.get("order_id")

            # 优先级1：通过 ObfuscatedAccountId 查找用户
            # 如果 app 端设置的是用户ID，可以直接使用；否则需要在数据库中存储映射关系
            # 这里假设 ObfuscatedAccountId 就是用户ID（app 端会设置用户ID）
            if obfuscated_account_id:
                # 方案A：直接使用 ObfuscatedAccountId 作为用户ID（如果 app 端设置的就是用户ID）
                # 先尝试直接作为用户ID查找
                result = await db.execute(
                    select(User).where(User.id == obfuscated_account_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    logger.debug(
                        f"通过 ObfuscatedAccountId 找到用户: {obfuscated_account_id}"
                    )
                    return user.id

                # 方案B：如果 ObfuscatedAccountId 不是用户ID，可以在用户表中添加字段存储映射
                # 或者创建单独的映射表（暂时不实现，等待实际需求）

            # 优先级2：通过邮箱查找用户
            if email_address:
                result = await db.execute(
                    select(User).where(User.email == email_address)
                )
                user = result.scalar_one_or_none()
                if user:
                    return user.id

            # 优先级3：通过Google用户ID查找
            if profile_id:
                result = await db.execute(
                    select(User).where(User.google_id == profile_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    return user.id

            # 优先级4：通过已有的订阅交易记录查找
            if order_id:
                result = await db.execute(
                    select(SubscriptionTransaction).where(
                        SubscriptionTransaction.google_play_order_id == order_id
                    )
                )
                transaction = result.scalar_one_or_none()
                if transaction:
                    return transaction.user_id

            logger.warning(
                f"无法从购买信息中推断用户ID: obfuscated_account_id={obfuscated_account_id}, "
                f"email={email_address}, profile_id={profile_id}, order_id={order_id}"
            )
            logger.debug(f"完整购买信息: {purchase_info}")
            return None

        except Exception as e:
            logger.error(f"推断用户ID失败: {str(e)}")
            return None

    async def _create_subscription_from_purchase_info(
        self,
        db: AsyncSession,
        user_id: str,
        plan: SubscriptionPlan,
        purchase_token: str,
        purchase_info: Dict[str, Any],
        notification_data: Dict[str, Any],
    ) -> Optional[UserSubscription]:
        """
        从购买信息创建订阅记录

        Args:
            db: 数据库会话
            user_id: 用户ID
            plan: 订阅计划
            purchase_token: 购买令牌
            purchase_info: 购买信息
            notification_data: 通知数据

        Returns:
            Optional[UserSubscription]: 创建的订阅记录或None
        """
        try:
            # 检查是否已经存在相同的购买令牌
            existing_subscription = await db.execute(
                select(UserSubscription).where(
                    UserSubscription.google_play_purchase_token
                    == purchase_token
                )
            )

            if existing_subscription.scalar_one_or_none():
                logger.warning(f"购买令牌已存在: {purchase_token}")
                return None

            # 取消用户当前的其他活跃订阅
            await self._cancel_user_active_subscriptions(db, user_id)

            # 创建新的订阅记录
            start_date = purchase_info.get("start_time") or datetime.now(
                timezone.utc
            )
            end_date = purchase_info.get("expiry_time")
            order_id = purchase_info.get("order_id")

            subscription = UserSubscription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                plan_id=plan.id,
                google_play_purchase_token=purchase_token,
                google_play_order_id=order_id,
                google_play_subscription_id=plan.google_play_product_id,
                status=SubscriptionStatus.ACTIVE,
                start_date=start_date,
                end_date=end_date,
                auto_renew=purchase_info.get("auto_renewing", True),
                extra_data=self._make_json_serializable(
                    {
                        "google_play_info": purchase_info,
                        "created_from_rtdn": True,
                        "rtdn_notification_data": notification_data,
                    }
                ),
            )

            db.add(subscription)

            # 创建交易记录
            transaction = SubscriptionTransaction(
                id=str(uuid.uuid4()),
                subscription_id=subscription.id,
                user_id=user_id,
                transaction_type=TransactionType.PURCHASE,
                amount=self._safe_convert_price_micros(
                    purchase_info.get("price_amount_micros", 0)
                ),
                currency=purchase_info.get("price_currency_code", "USD"),
                google_play_purchase_token=purchase_token,
                google_play_order_id=order_id,
                status="COMPLETED",
                transaction_time=start_date,
                extra_data=self._make_json_serializable(
                    {
                        "google_play_info": purchase_info,
                        "created_from_rtdn": True,
                        "rtdn_notification_data": notification_data,
                    }
                ),
            )

            db.add(transaction)

            await db.commit()

            # 重新查询订阅记录，确保 plan 关系已预加载（避免后续访问 subscription.plan 触发懒加载）
            result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(UserSubscription.id == subscription.id)
            )
            subscription = result.scalar_one()

            # 确认购买（向Google Play发送确认）
            try:
                self.google_play_service.acknowledge_subscription(
                    plan.google_play_product_id, purchase_token
                )
            except Exception as e:
                logger.warning(f"确认购买失败，但订阅记录已创建: {str(e)}")

            logger.info(
                f"从RTDN通知创建订阅成功 - 用户: {user_id}, 订阅: {subscription.id}"
            )

            return subscription

        except Exception as e:
            await db.rollback()
            logger.error(f"从购买信息创建订阅记录失败: {str(e)}")
            return None

    async def _update_subscription_by_notification_type(
        self,
        db: AsyncSession,
        subscription: UserSubscription,
        notification_type: int,
        notification_data: Dict[str, Any],
    ) -> None:
        """根据通知类型更新订阅状态"""
        try:
            # 防御式获取 plan（避免懒加载触发 greenlet_spawn 错误）
            plan = subscription.plan
            if plan is None:
                result = await db.execute(
                    select(SubscriptionPlan).where(
                        SubscriptionPlan.id == subscription.plan_id
                    )
                )
                plan = result.scalar_one_or_none()
                if plan is None:
                    logger.error(
                        f"更新订阅状态失败 - 找不到订阅计划: plan_id={subscription.plan_id}"
                    )
                    raise ValueError(
                        f"Subscription plan not found: {subscription.plan_id}"
                    )

            # Google Play通知类型映射
            # 1: SUBSCRIPTION_RECOVERED (订阅恢复)
            # 2: SUBSCRIPTION_RENEWED (订阅续费)
            # 3: SUBSCRIPTION_CANCELED (订阅取消)
            # 4: SUBSCRIPTION_PURCHASED (订阅购买)
            # 5: SUBSCRIPTION_ON_HOLD (订阅暂停)
            # 6: SUBSCRIPTION_IN_GRACE_PERIOD (宽限期)
            # 7: SUBSCRIPTION_RESTARTED (订阅重启)
            # 8: SUBSCRIPTION_PRICE_CHANGE_CONFIRMED (价格变更确认)
            # 9: SUBSCRIPTION_DEFERRED (订阅延期)
            # 10: SUBSCRIPTION_PAUSED (订阅暂停)
            # 11: SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED (暂停计划变更)
            # 12: SUBSCRIPTION_REVOKED (订阅撤销)
            # 13: SUBSCRIPTION_EXPIRED (订阅过期)
            # 14: SUBSCRIPTION_REFUNDED (订阅退款)

            if notification_type in [1, 2, 4, 7]:  # 恢复、续费、购买、重启
                subscription.status = SubscriptionStatus.ACTIVE

                # 恢复或重启时重新启用自动续费
                if notification_type in [
                    1,
                    7,
                ]:  # SUBSCRIPTION_RECOVERED, SUBSCRIPTION_RESTARTED
                    subscription.auto_renew = True
                    logger.info(
                        f"订阅恢复/重启 - 订阅: {subscription.id}, 类型: {notification_type}"
                    )

                # 如果是续费，创建续费交易记录
                if notification_type == 2:
                    await self._create_renewal_transaction(
                        db, subscription, notification_data
                    )

            elif notification_type == 3:  # 取消
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.auto_renew = False

            elif notification_type in [5, 10]:  # 暂停
                subscription.status = SubscriptionStatus.PAUSED

            elif notification_type == 6:  # 宽限期
                subscription.status = SubscriptionStatus.GRACE_PERIOD

            elif notification_type in [12, 13]:  # 撤销、过期
                subscription.status = SubscriptionStatus.EXPIRED

            elif notification_type == 14:  # 退款
                await self.handle_refund(db, subscription, notification_data)
                return  # 退款处理包含了commit，直接返回

            # 获取最新的订阅信息
            latest_info = self.google_play_service.get_subscription_details(
                plan.google_play_product_id,
                subscription.google_play_purchase_token,
            )

            if "error" not in latest_info:
                subscription.end_date = latest_info.get("expiry_time")
                subscription.auto_renew = latest_info.get(
                    "auto_renewing", False
                )

                # 更新元数据
                extra_data = subscription.extra_data or {}
                extra_data["last_notification"] = {
                    "type": notification_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": notification_data,
                }
                subscription.extra_data = self._make_json_serializable(
                    extra_data
                )

            await db.commit()

            logger.info(
                f"订阅状态更新成功 - 订阅: {subscription.id}, 类型: {notification_type}"
            )

        except Exception as e:
            await db.rollback()
            logger.error(
                f"更新订阅状态失败: {str(e)}, notification_type: {notification_type}"
            )
            raise

    async def _create_renewal_transaction(
        self,
        db: AsyncSession,
        subscription: UserSubscription,
        notification_data: Dict[str, Any],
    ) -> None:
        """创建续费交易记录"""
        try:
            # 防御式获取 plan（避免懒加载触发 greenlet_spawn 错误）
            plan = subscription.plan
            if plan is None:
                result = await db.execute(
                    select(SubscriptionPlan).where(
                        SubscriptionPlan.id == subscription.plan_id
                    )
                )
                plan = result.scalar_one_or_none()
                if plan is None:
                    logger.error(
                        f"创建续费交易记录失败 - 找不到订阅计划: plan_id={subscription.plan_id}"
                    )
                    raise ValueError(
                        f"Subscription plan not found: {subscription.plan_id}"
                    )

            transaction = SubscriptionTransaction(
                id=str(uuid.uuid4()),
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                transaction_type=TransactionType.RENEWAL,
                amount=plan.price,
                currency=plan.currency,
                google_play_purchase_token=subscription.google_play_purchase_token,
                status="COMPLETED",
                transaction_time=datetime.now(timezone.utc),
                extra_data={"notification_data": notification_data},
            )

            db.add(transaction)
            logger.debug(f"创建续费交易记录成功 - 订阅: {subscription.id}")

        except Exception as e:
            logger.error(f"创建续费交易记录失败: {str(e)}")
            raise

    async def handle_refund(
        self,
        db: AsyncSession,
        subscription: UserSubscription,
        refund_data: Dict[str, Any],
    ) -> None:
        """处理退款逻辑"""
        try:
            # 防御式获取 plan（避免懒加载触发 greenlet_spawn 错误）
            plan = subscription.plan
            if plan is None:
                result = await db.execute(
                    select(SubscriptionPlan).where(
                        SubscriptionPlan.id == subscription.plan_id
                    )
                )
                plan = result.scalar_one_or_none()
                if plan is None:
                    logger.error(
                        f"退款处理失败 - 找不到订阅计划: plan_id={subscription.plan_id}"
                    )
                    raise ValueError(
                        f"Subscription plan not found: {subscription.plan_id}"
                    )

            # 更新订阅状态为退款
            subscription.status = SubscriptionStatus.REFUNDED
            subscription.auto_renew = False

            # 设置结束时间为当前时间（立即生效）
            subscription.end_date = datetime.now(timezone.utc)

            # 创建退款交易记录
            refund_amount = refund_data.get("amount") or plan.price

            transaction = SubscriptionTransaction(
                id=str(uuid.uuid4()),
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                transaction_type=TransactionType.REFUND,
                amount=-abs(refund_amount),  # 退款金额为负数
                currency=plan.currency,
                google_play_purchase_token=subscription.google_play_purchase_token,
                google_play_order_id=subscription.google_play_order_id,
                status="COMPLETED",
                transaction_time=datetime.now(timezone.utc),
                extra_data={"refund_data": refund_data},
            )

            db.add(transaction)

            # 更新订阅的元数据
            extra_data = subscription.extra_data or {}
            extra_data["refund_info"] = {
                "refunded_at": datetime.now(timezone.utc).isoformat(),
                "refund_amount": refund_amount,
                "refund_data": refund_data,
            }
            subscription.extra_data = self._make_json_serializable(extra_data)

            await db.commit()

            logger.info(
                f"退款处理成功 - 订阅: {subscription.id}, 金额: {refund_amount}"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"退款处理失败: {str(e)}")
            raise

    async def process_google_play_refund_notification(
        self, db: AsyncSession, notification_data: Dict[str, Any]
    ) -> bool:
        """处理Google Play退款通知"""
        try:
            # 解析退款通知数据
            one_time_product_notification = notification_data.get(
                "oneTimeProductNotification"
            )
            subscription_notification = notification_data.get(
                "subscriptionNotification"
            )

            if subscription_notification:
                purchase_token = subscription_notification.get("purchaseToken")
                notification_type = subscription_notification.get(
                    "notificationType"
                )

                # Google Play通知类型14通常表示退款
                if notification_type == 14:  # SUBSCRIPTION_REFUNDED
                    # 查找对应的订阅记录
                    result = await db.execute(
                        select(UserSubscription)
                        .options(selectinload(UserSubscription.plan))
                        .where(
                            UserSubscription.google_play_purchase_token
                            == purchase_token
                        )
                    )
                    subscription = result.scalar_one_or_none()

                    if subscription:
                        await self.handle_refund(
                            db, subscription, notification_data
                        )
                        return True
                    else:
                        logger.warning(
                            f"未找到对应的订阅记录用于退款: {purchase_token}"
                        )

            elif one_time_product_notification:
                # 处理一次性产品退款
                purchase_token = one_time_product_notification.get(
                    "purchaseToken"
                )
                notification_type = one_time_product_notification.get(
                    "notificationType"
                )

                if (
                    notification_type == 3
                ):  # ONE_TIME_PRODUCT_CANCELED (可能包含退款)
                    logger.info(f"收到一次性产品退款通知: {purchase_token}")
                    # 这里可以添加一次性产品退款处理逻辑

            return False

        except Exception as e:
            logger.error(f"处理Google Play退款通知失败: {str(e)}")
            return False

    async def manual_refund(
        self,
        db: AsyncSession,
        subscription_id: str,
        refund_amount: Optional[float] = None,
        reason: str = "manual_refund",
    ) -> bool:
        """手动处理退款（管理员功能）"""
        try:
            # 查找订阅记录
            result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(UserSubscription.id == subscription_id)
            )
            subscription = result.scalar_one_or_none()

            if not subscription:
                logger.error(f"未找到订阅记录: {subscription_id}")
                return False

            if subscription.status == SubscriptionStatus.REFUNDED:
                logger.warning(f"订阅已经是退款状态: {subscription_id}")
                return False

            # 准备退款数据
            refund_data = {
                "amount": refund_amount or subscription.plan.price,
                "reason": reason,
                "type": "manual",
                "processed_by": "admin",
            }

            await self.handle_refund(db, subscription, refund_data)
            return True

        except Exception as e:
            logger.error(f"手动退款处理失败: {str(e)}")
            return False

    def _safe_convert_price_micros(self, price_micros: Any) -> float:
        """
        安全转换Google Play价格（微单位）为实际金额

        Args:
            price_micros: 价格微单位（可能是字符串或整数）

        Returns:
            float: 实际金额
        """
        try:
            if price_micros is None:
                return 0.0

            # 转换为整数
            if isinstance(price_micros, str):
                price_int = int(price_micros)
            elif isinstance(price_micros, (int, float)):
                price_int = int(price_micros)
            else:
                logger.warning(
                    f"无法识别的价格格式: {price_micros}, 类型: {type(price_micros)}"
                )
                return 0.0

            # 转换为实际金额（微单位除以1,000,000）
            return price_int / 1_000_000

        except (ValueError, TypeError) as e:
            logger.error(f"价格转换失败: {price_micros}, 错误: {str(e)}")
            return 0.0

    async def recover_orphaned_subscriptions(
        self, db: AsyncSession, user_id: str, email: str, google_id: str
    ) -> int:
        """
        恢复孤立的订阅记录

        当用户重新登录时，检查是否有使用相同邮箱或Google ID的孤立订阅记录，
        并将这些订阅关联到当前用户账户

        Args:
            db: 数据库会话
            user_id: 当前用户ID
            email: 用户邮箱
            google_id: Google账户ID

        Returns:
            int: 恢复的订阅记录数量
        """
        try:
            recovered_count = 0

            # 查找使用相同邮箱的其他用户的活跃订阅
            if email:
                email_users_result = await db.execute(
                    select(User).where(
                        and_(
                            User.email == email,
                            User.id != user_id,
                            User.deleted_at.is_(None),
                        )
                    )
                )
                email_users = email_users_result.scalars().all()

                # 查找这些用户的活跃订阅
                for old_user in email_users:
                    subscriptions_result = await db.execute(
                        select(UserSubscription).where(
                            and_(
                                UserSubscription.user_id == old_user.id,
                                UserSubscription.status.in_(
                                    [
                                        SubscriptionStatus.ACTIVE,
                                        SubscriptionStatus.CANCELLED,
                                    ]
                                ),
                                or_(
                                    UserSubscription.end_date.is_(None),
                                    UserSubscription.end_date
                                    > datetime.now(timezone.utc),
                                ),
                            )
                        )
                    )
                    subscriptions = subscriptions_result.scalars().all()

                    # 转移订阅到当前用户
                    for subscription in subscriptions:
                        old_user_id = subscription.user_id
                        subscription.user_id = user_id

                        # 更新元数据记录恢复信息
                        extra_data = subscription.extra_data or {}
                        extra_data["recovered_subscription"] = {
                            "recovered_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                            "original_user_id": old_user_id,
                            "recovery_method": "email_match",
                            "user_email": email,
                        }
                        subscription.extra_data = self._make_json_serializable(
                            extra_data
                        )

                        recovered_count += 1
                        logger.info(
                            f"恢复订阅记录: {subscription.id} 从用户 {old_user_id} 到用户 {user_id}"
                        )

            # 查找使用相同Google ID的其他用户的活跃订阅
            if google_id:
                google_users_result = await db.execute(
                    select(User).where(
                        and_(
                            User.google_id == google_id,
                            User.id != user_id,
                            User.deleted_at.is_(None),
                        )
                    )
                )
                google_users = google_users_result.scalars().all()

                # 查找这些用户的活跃订阅（避免重复处理已通过邮箱处理的用户）
                processed_user_ids = set()
                if email:
                    processed_user_ids.update([u.id for u in email_users])

                for old_user in google_users:
                    if old_user.id in processed_user_ids:
                        continue  # 已经通过邮箱处理过

                    subscriptions_result = await db.execute(
                        select(UserSubscription).where(
                            and_(
                                UserSubscription.user_id == old_user.id,
                                UserSubscription.status.in_(
                                    [
                                        SubscriptionStatus.ACTIVE,
                                        SubscriptionStatus.CANCELLED,
                                    ]
                                ),
                                or_(
                                    UserSubscription.end_date.is_(None),
                                    UserSubscription.end_date
                                    > datetime.now(timezone.utc),
                                ),
                            )
                        )
                    )
                    subscriptions = subscriptions_result.scalars().all()

                    # 转移订阅到当前用户
                    for subscription in subscriptions:
                        old_user_id = subscription.user_id
                        subscription.user_id = user_id

                        # 更新元数据记录恢复信息
                        extra_data = subscription.extra_data or {}
                        extra_data["recovered_subscription"] = {
                            "recovered_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                            "original_user_id": old_user_id,
                            "recovery_method": "google_id_match",
                            "google_id": google_id,
                        }
                        subscription.extra_data = self._make_json_serializable(
                            extra_data
                        )

                        recovered_count += 1
                        logger.info(
                            f"恢复订阅记录: {subscription.id} 从用户 {old_user_id} 到用户 {user_id}"
                        )

            if recovered_count > 0:
                await db.commit()
                logger.info(
                    f"用户 {user_id} 恢复了 {recovered_count} 个订阅记录"
                )

            return recovered_count

        except Exception as e:
            await db.rollback()
            logger.error(f"恢复孤立订阅失败: {str(e)}")
            return 0

    def _make_json_serializable(self, data: Any) -> Any:
        """
        将数据转换为JSON可序列化的格式

        Args:
            data: 需要转换的数据

        Returns:
            JSON可序列化的数据
        """
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {
                key: self._make_json_serializable(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, tuple):
            return [self._make_json_serializable(item) for item in data]
        elif hasattr(data, "__dict__"):
            # 处理自定义对象
            return self._make_json_serializable(data.__dict__)
        else:
            # 基本数据类型（str, int, float, bool, None）
            return data

            return data
