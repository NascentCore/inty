import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
import json
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.subscription import (
    SubscriptionPlan,
    UserSubscription,
    SubscriptionTransaction,
    SubscriptionUsage,
    SubscriptionStatus,
    TransactionType,
    SubscriptionPlanType
)
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionPlanCreate,
    UserSubscriptionCreate,
    SubscriptionTransactionCreate,
    SubscriptionUsageCreate,
    GooglePlayPurchaseRequest,
    SubscriptionStatusResponse,
    UsageStatisticsResponse,
    PurchaseVerificationResponse,
    FeatureInfo
)
from app.models.subscription_features import SubscriptionFeatures
from app.services.google_play_service import google_play_service

logger = logging.getLogger(__name__)


class SubscriptionService:
    """订阅服务"""
    
    async def get_subscription_plans(
        self, 
        db: AsyncSession, 
        include_inactive: bool = False
    ) -> List[SubscriptionPlan]:
        """获取订阅计划列表"""
        try:
            query = select(SubscriptionPlan)
            
            if not include_inactive:
                query = query.where(SubscriptionPlan.is_active == True)
            
            query = query.order_by(SubscriptionPlan.sort_order, SubscriptionPlan.created_at)
            
            result = await db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"获取订阅计划列表失败: {str(e)}")
            raise
    
    async def get_subscription_plan(
        self, 
        db: AsyncSession, 
        plan_id: str
    ) -> Optional[SubscriptionPlan]:
        """根据ID获取订阅计划"""
        try:
            result = await db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取订阅计划失败: {str(e)}")
            raise
    
    async def get_subscription_plan_by_product_id(
        self, 
        db: AsyncSession, 
        product_id: str
    ) -> Optional[SubscriptionPlan]:
        """根据Google Play产品ID获取订阅计划"""
        try:
            result = await db.execute(
                select(SubscriptionPlan).where(
                    SubscriptionPlan.google_play_product_id == product_id
                )
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"根据产品ID获取订阅计划失败: {str(e)}")
            raise
    
    async def create_subscription_plan(
        self, 
        db: AsyncSession, 
        plan_data: SubscriptionPlanCreate
    ) -> SubscriptionPlan:
        """创建订阅计划"""
        try:
            plan = SubscriptionPlan(
                id=str(uuid.uuid4()),
                **plan_data.model_dump()
            )
            
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            
            logger.info(f"创建订阅计划成功: {plan.id}")
            return plan
            
        except Exception as e:
            await db.rollback()
            logger.error(f"创建订阅计划失败: {str(e)}")
            raise
    
    async def get_user_current_subscription(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> Optional[UserSubscription]:
        """获取用户当前有效的订阅"""
        try:
            result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(
                    and_(
                        UserSubscription.user_id == user_id,
                        UserSubscription.status == SubscriptionStatus.ACTIVE,
                        or_(
                            UserSubscription.end_date.is_(None),
                            UserSubscription.end_date > datetime.now(timezone.utc)
                        )
                    )
                )
                .order_by(UserSubscription.created_at.desc())
            )
            
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取用户当前订阅失败: {str(e)}")
            raise
    
    async def get_user_subscription_status(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> SubscriptionStatusResponse:
        """获取用户订阅状态"""
        try:
            # 获取当前有效订阅
            subscription = await self.get_user_current_subscription(db, user_id)
            
            if subscription:
                remaining_days = None
                if subscription.end_date:
                    delta = subscription.end_date - datetime.now(timezone.utc)
                    remaining_days = max(0, delta.days)
                
                # 付费用户获得所有权益
                feature_list = []
                for feature_data in SubscriptionFeatures.get_premium_features_list():
                    feature_list.append(FeatureInfo(
                        key=feature_data["key"],
                        name=feature_data["name"],
                        description=feature_data["description"],
                        type=feature_data["type"],
                        icon=feature_data["icon"],
                        order=feature_data["order"],
                        enabled=True
                    ))
                
                return SubscriptionStatusResponse(
                    is_subscribed=True,
                    subscription=subscription,
                    plan=subscription.plan,
                    remaining_days=remaining_days,
                    chat_limit_per_day=subscription.plan.chat_limit_per_day,
                    total_chat_limit=None,  # 付费用户不使用总次数限制
                    agent_creation_limit=subscription.plan.agent_creation_limit,
                    features=subscription.plan.features or {},
                    feature_list=feature_list
                )
            else:
                # 免费用户的默认限制
                # 免费用户只启用真实权益，虚假权益显示但不启用
                feature_list = []
                for feature_data in SubscriptionFeatures.get_premium_features_list():
                    is_real_feature = SubscriptionFeatures.is_real_feature(feature_data["key"])
                    feature_list.append(FeatureInfo(
                        key=feature_data["key"],
                        name=feature_data["name"],
                        description=feature_data["description"],
                        type=feature_data["type"],
                        icon=feature_data["icon"],
                        order=feature_data["order"],
                        enabled=is_real_feature  # 只有真实权益才启用
                    ))
                
                return SubscriptionStatusResponse(
                    is_subscribed=False,
                    subscription=None,
                    plan=None,
                    remaining_days=None,
                    chat_limit_per_day=-1,  # 免费用户不限制每日聊天次数
                    total_chat_limit=100,  # 免费用户总聊天次数限制100次
                    agent_creation_limit=6,  # 免费用户最多创建6个Agent
                    features={},
                    feature_list=feature_list
                )
                
        except Exception as e:
            logger.error(f"获取用户订阅状态失败: {str(e)}")
            raise
    
    async def verify_and_create_subscription(
        self, 
        db: AsyncSession, 
        user_id: str, 
        purchase_request: GooglePlayPurchaseRequest
    ) -> PurchaseVerificationResponse:
        """验证购买并创建订阅"""
        try:
            # 查找对应的订阅计划
            plan = await self.get_subscription_plan_by_product_id(
                db, purchase_request.product_id
            )
            
            if not plan:
                return PurchaseVerificationResponse(
                    is_valid=False,
                    subscription=None,
                    message="未找到对应的订阅计划",
                    error_code="PLAN_NOT_FOUND"
                )
            
            # 调用Google Play API验证购买
            is_valid, purchase_info = google_play_service.verify_subscription_purchase(
                purchase_request.product_id, 
                purchase_request.purchase_token
            )
            
            if not is_valid:
                return PurchaseVerificationResponse(
                    is_valid=False,
                    subscription=None,
                    message="Google Play购买验证失败",
                    error_code="GOOGLE_PLAY_VERIFICATION_FAILED"
                )
            
            # 检查是否已经存在相同的购买令牌
            existing_subscription = await db.execute(
                select(UserSubscription).where(
                    UserSubscription.google_play_purchase_token == purchase_request.purchase_token
                )
            )
            
            if existing_subscription.scalar_one_or_none():
                return PurchaseVerificationResponse(
                    is_valid=False,
                    subscription=None,
                    message="该购买令牌已被使用",
                    error_code="DUPLICATE_PURCHASE_TOKEN"
                )
            
            # 取消用户当前的其他活跃订阅
            await self._cancel_user_active_subscriptions(db, user_id)
            
            # 创建新的订阅记录
            start_date = purchase_info.get("start_time") or datetime.now(timezone.utc)
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
                extra_data={"google_play_info": self._make_json_serializable(purchase_info)}
            )
            
            db.add(subscription)
            
            # 创建交易记录
            transaction = SubscriptionTransaction(
                id=str(uuid.uuid4()),
                subscription_id=subscription.id,
                user_id=user_id,
                transaction_type=TransactionType.PURCHASE,
                amount=self._safe_convert_price_micros(purchase_info.get("price_amount_micros", 0)),  # 转换为实际金额
                currency=purchase_info.get("price_currency_code", "USD"),
                google_play_purchase_token=purchase_request.purchase_token,
                google_play_order_id=purchase_request.order_id,
                status="COMPLETED",
                transaction_time=start_date,
                extra_data={"google_play_info": self._make_json_serializable(purchase_info)}
            )
            
            db.add(transaction)
            
            await db.commit()
            await db.refresh(subscription)
            
            # 确认购买（向Google Play发送确认）
            google_play_service.acknowledge_subscription(
                purchase_request.product_id, 
                purchase_request.purchase_token
            )
            
            logger.info(f"订阅创建成功 - 用户: {user_id}, 订阅: {subscription.id}")
            
            return PurchaseVerificationResponse(
                is_valid=True,
                subscription=subscription,
                message="订阅创建成功"
            )
            
        except Exception as e:
            await db.rollback()
            logger.error(f"验证购买并创建订阅失败: {str(e)}")
            return PurchaseVerificationResponse(
                is_valid=False,
                subscription=None,
                message="服务器内部错误",
                error_code="INTERNAL_ERROR"
            )
    
    async def _cancel_user_active_subscriptions(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> None:
        """取消用户当前的所有活跃订阅"""
        try:
            # 查询用户的所有活跃订阅
            result = await db.execute(
                select(UserSubscription).where(
                    and_(
                        UserSubscription.user_id == user_id,
                        UserSubscription.status == SubscriptionStatus.ACTIVE
                    )
                )
            )
            
            active_subscriptions = result.scalars().all()
            
            for subscription in active_subscriptions:
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.auto_renew = False
                
            if active_subscriptions:
                logger.info(f"取消用户 {user_id} 的 {len(active_subscriptions)} 个活跃订阅")
                
        except Exception as e:
            logger.error(f"取消用户活跃订阅失败: {str(e)}")
            raise
    
    async def record_usage(
        self, 
        db: Optional[AsyncSession], 
        user_id: str, 
        usage_type: str, 
        usage_count: int = 1,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Optional[SubscriptionUsage]:
        """记录用户使用情况"""
        # 如果没有提供数据库会话，创建新的会话
        if db is None:
            from app.api.deps import get_async_db
            async for db_session in get_async_db():
                return await self._record_usage_impl(
                    db_session, user_id, usage_type, usage_count, extra_data
                )
        else:
            return await self._record_usage_impl(
                db, user_id, usage_type, usage_count, extra_data
            )
    
    async def _record_usage_impl(
        self, 
        db: AsyncSession, 
        user_id: str, 
        usage_type: str, 
        usage_count: int = 1,
        extra_data: Optional[Dict[str, Any]] = None
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
                extra_data=extra_data or {}
            )
            
            db.add(usage)
            await db.commit()
            await db.refresh(usage)
            
            return usage
            
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass  # 如果rollback也失败，忽略
            logger.error(f"记录用户使用情况失败: {str(e)}")
            return None  # 返回None而不是抛异常，避免影响主流程
    
    async def get_user_usage_statistics(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> UsageStatisticsResponse:
        """获取用户使用统计"""
        try:
            # 获取订阅状态
            subscription_status = await self.get_user_subscription_status(db, user_id)
            
            # 获取今日聊天次数
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = today_start + timedelta(days=1)
            
            chat_count_result = await db.execute(
                select(func.sum(SubscriptionUsage.usage_count))
                .where(
                    and_(
                        SubscriptionUsage.user_id == user_id,
                        SubscriptionUsage.usage_type == "chat",
                        SubscriptionUsage.usage_date >= today_start,
                        SubscriptionUsage.usage_date < today_end
                    )
                )
            )
            today_chat_count = chat_count_result.scalar() or 0
            
            # 获取用户总聊天次数（免费用户需要）
            total_chat_count = None
            if subscription_status.total_chat_limit is not None:
                total_chat_count_result = await db.execute(
                    select(func.sum(SubscriptionUsage.usage_count))
                    .where(
                        and_(
                            SubscriptionUsage.user_id == user_id,
                            SubscriptionUsage.usage_type == "chat"
                        )
                    )
                )
                total_chat_count = total_chat_count_result.scalar() or 0
            
            # 获取用户创建的Agent数量
            from app.models.agent import Agent
            agent_count_result = await db.execute(
                select(func.count(Agent.id))
                .where(
                    and_(
                        Agent.creator_id == user_id,
                        Agent.deleted_at.is_(None)
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
            
            return UsageStatisticsResponse(
                today_chat_count=today_chat_count,
                today_limit=subscription_status.chat_limit_per_day,
                total_chat_count=total_chat_count,
                total_chat_limit=subscription_status.total_chat_limit,
                agent_count=agent_count,
                agent_limit=subscription_status.agent_creation_limit,
                usage_history=list(usage_history)
            )
            
        except Exception as e:
            logger.error(f"获取用户使用统计失败: {str(e)}")
            raise
    
    async def check_chat_limit(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> Tuple[bool, int, int]:
        """
        检查用户聊天次数限制
        
        Returns:
            Tuple[bool, int, int]: (是否允许聊天, 已用次数, 限制次数)
        """
        try:
            # 获取订阅状态
            subscription_status = await self.get_user_subscription_status(db, user_id)
            
            # 免费用户：检查总聊天次数限制
            if subscription_status.total_chat_limit is not None:
                # 获取用户总聊天次数
                total_chat_count_result = await db.execute(
                    select(func.sum(SubscriptionUsage.usage_count))
                    .where(
                        and_(
                            SubscriptionUsage.user_id == user_id,
                            SubscriptionUsage.usage_type == "chat"
                        )
                    )
                )
                total_chat_count = total_chat_count_result.scalar() or 0
                
                # 检查是否超出总限制
                is_allowed = total_chat_count < subscription_status.total_chat_limit
                
                return is_allowed, total_chat_count, subscription_status.total_chat_limit
            
            # 付费用户：检查每日聊天次数限制
            # 如果是无限制，直接返回允许
            if subscription_status.chat_limit_per_day == -1:
                return True, 0, -1
            
            # 获取今日聊天次数
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = today_start + timedelta(days=1)
            
            chat_count_result = await db.execute(
                select(func.sum(SubscriptionUsage.usage_count))
                .where(
                    and_(
                        SubscriptionUsage.user_id == user_id,
                        SubscriptionUsage.usage_type == "chat",
                        SubscriptionUsage.usage_date >= today_start,
                        SubscriptionUsage.usage_date < today_end
                    )
                )
            )
            today_chat_count = chat_count_result.scalar() or 0
            
            # 检查是否超出限制
            is_allowed = today_chat_count < subscription_status.chat_limit_per_day
            
            return is_allowed, today_chat_count, subscription_status.chat_limit_per_day
            
        except Exception as e:
            logger.error(f"检查聊天次数限制失败: {str(e)}")
            # 出错时默认允许，避免影响用户体验
            return True, 0, -1
    
    async def check_agent_creation_limit(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> Tuple[bool, int, int]:
        """
        检查用户Agent创建数量限制
        
        Returns:
            Tuple[bool, int, int]: (是否允许创建, 已创建数量, 限制数量)
        """
        try:
            # 获取订阅状态
            subscription_status = await self.get_user_subscription_status(db, user_id)
            
            # 获取用户创建的Agent数量
            from app.models.agent import Agent
            agent_count_result = await db.execute(
                select(func.count(Agent.id))
                .where(
                    and_(
                        Agent.creator_id == user_id,
                        Agent.deleted_at.is_(None)
                    )
                )
            )
            agent_count = agent_count_result.scalar() or 0
            
            # 检查是否超出限制
            is_allowed = agent_count < subscription_status.agent_creation_limit
            
            return is_allowed, agent_count, subscription_status.agent_creation_limit
            
        except Exception as e:
            logger.error(f"检查Agent创建数量限制失败: {str(e)}")
            # 出错时默认允许，避免影响用户体验
            return True, 0, 6
    
    async def handle_subscription_notification(
        self, 
        db: AsyncSession, 
        notification_data: Dict[str, Any]
    ) -> bool:
        """处理Google Play订阅状态变化通知"""
        try:
            # 首先检查是否是退款通知
            refund_handled = await self.process_google_play_refund_notification(db, notification_data)
            if refund_handled:
                return True
                
            subscription_notification = notification_data.get("subscriptionNotification")
            if not subscription_notification:
                return False
            
            purchase_token = subscription_notification.get("purchaseToken")
            notification_type = subscription_notification.get("notificationType")
            
            if not purchase_token:
                return False
            
            # 查找对应的订阅记录
            result = await db.execute(
                select(UserSubscription)
                .options(selectinload(UserSubscription.plan))
                .where(UserSubscription.google_play_purchase_token == purchase_token)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                logger.warning(f"未找到对应的订阅记录: {purchase_token}, 通知类型: {notification_type}")
                
                # 尝试自动创建订阅记录
                subscription = await self._try_create_subscription_from_notification(
                    db, purchase_token, notification_type, notification_data
                )
                
                if not subscription:
                    logger.error(f"无法为购买令牌创建订阅记录: {purchase_token}")
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
        notification_data: Dict[str, Any]
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
            if notification_type not in [1, 2, 4]:
                logger.info(f"通知类型 {notification_type} 不适合创建订阅记录")
                return None
            
            # 从通知数据中尝试提取产品ID（用于日志记录）
            subscription_notification = notification_data.get("subscriptionNotification", {})
            logger.debug(f"处理订阅通知: {subscription_notification}")
            
            # 获取所有订阅计划以匹配产品ID
            plans = await self.get_subscription_plans(db, include_inactive=True)
            
            subscription_created = None
            
            # 遍历所有订阅计划，尝试验证购买
            for plan in plans:
                try:
                    # 使用Google Play API验证购买
                    is_valid, purchase_info = google_play_service.verify_subscription_purchase(
                        plan.google_play_product_id, purchase_token
                    )
                    
                    if is_valid and "error" not in purchase_info:
                        logger.info(f"找到匹配的订阅计划: {plan.id}, 产品ID: {plan.google_play_product_id}")
                        
                        # 尝试从购买信息中推断用户ID
                        user_id = await self._infer_user_id_from_purchase_info(db, purchase_info)
                        
                        if not user_id:
                            logger.warning(f"无法从购买信息中推断用户ID: {purchase_token}")
                            continue
                        
                        # 创建订阅记录
                        subscription_created = await self._create_subscription_from_purchase_info(
                            db, user_id, plan, purchase_token, purchase_info, notification_data
                        )
                        
                        if subscription_created:
                            logger.info(f"成功创建订阅记录: {subscription_created.id}")
                            break
                        
                except Exception as e:
                    logger.debug(f"验证计划 {plan.id} 失败: {str(e)}")
                    continue
            
            return subscription_created
            
        except Exception as e:
            logger.error(f"从通知创建订阅记录失败: {str(e)}")
            return None
    
    async def _infer_user_id_from_purchase_info(
        self,
        db: AsyncSession,
        purchase_info: Dict[str, Any]
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
            email_address = purchase_info.get("email_address")
            profile_id = purchase_info.get("profile_id")
            order_id = purchase_info.get("order_id")
            
            # 首先尝试通过邮箱查找用户
            if email_address:
                result = await db.execute(
                    select(User).where(User.email == email_address)
                )
                user = result.scalar_one_or_none()
                if user:
                    return user.id
            
            # 尝试通过Google用户ID查找
            if profile_id:
                result = await db.execute(
                    select(User).where(User.google_user_id == profile_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    return user.id
            
            # 尝试通过已有的订阅交易记录查找
            if order_id:
                result = await db.execute(
                    select(SubscriptionTransaction).where(
                        SubscriptionTransaction.google_play_order_id == order_id
                    )
                )
                transaction = result.scalar_one_or_none()
                if transaction:
                    return transaction.user_id
            
            logger.warning(f"无法从购买信息中推断用户ID: email={email_address}, profile_id={profile_id}, order_id={order_id}")
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
        notification_data: Dict[str, Any]
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
                    UserSubscription.google_play_purchase_token == purchase_token
                )
            )
            
            if existing_subscription.scalar_one_or_none():
                logger.warning(f"购买令牌已存在: {purchase_token}")
                return None
            
            # 取消用户当前的其他活跃订阅
            await self._cancel_user_active_subscriptions(db, user_id)
            
            # 创建新的订阅记录
            start_date = purchase_info.get("start_time") or datetime.now(timezone.utc)
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
                extra_data=self._make_json_serializable({
                    "google_play_info": purchase_info,
                    "created_from_rtdn": True,
                    "rtdn_notification_data": notification_data
                })
            )
            
            db.add(subscription)
            
            # 创建交易记录
            transaction = SubscriptionTransaction(
                id=str(uuid.uuid4()),
                subscription_id=subscription.id,
                user_id=user_id,
                transaction_type=TransactionType.PURCHASE,
                amount=self._safe_convert_price_micros(purchase_info.get("price_amount_micros", 0)),
                currency=purchase_info.get("price_currency_code", "USD"),
                google_play_purchase_token=purchase_token,
                google_play_order_id=order_id,
                status="COMPLETED",
                transaction_time=start_date,
                extra_data=self._make_json_serializable({
                    "google_play_info": purchase_info,
                    "created_from_rtdn": True,
                    "rtdn_notification_data": notification_data
                })
            )
            
            db.add(transaction)
            
            await db.commit()
            await db.refresh(subscription)
            
            # 确认购买（向Google Play发送确认）
            try:
                google_play_service.acknowledge_subscription(
                    plan.google_play_product_id, purchase_token
                )
            except Exception as e:
                logger.warning(f"确认购买失败，但订阅记录已创建: {str(e)}")
            
            logger.info(f"从RTDN通知创建订阅成功 - 用户: {user_id}, 订阅: {subscription.id}")
            
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
        notification_data: Dict[str, Any]
    ) -> None:
        """根据通知类型更新订阅状态"""
        try:
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
                
                # 如果是续费，创建续费交易记录
                if notification_type == 2:
                    await self._create_renewal_transaction(db, subscription, notification_data)
                    
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
            latest_info = google_play_service.get_subscription_details(
                subscription.plan.google_play_product_id,
                subscription.google_play_purchase_token
            )
            
            if "error" not in latest_info:
                subscription.end_date = latest_info.get("expiry_time")
                subscription.auto_renew = latest_info.get("auto_renewing", False)
                
                # 更新元数据
                extra_data = subscription.extra_data or {}
                extra_data["last_notification"] = {
                    "type": notification_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": notification_data
                }
                subscription.extra_data = self._make_json_serializable(extra_data)
            
            await db.commit()
            
            logger.info(f"订阅状态更新成功 - 订阅: {subscription.id}, 类型: {notification_type}")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"更新订阅状态失败: {str(e)}")
            raise
    
    async def _create_renewal_transaction(
        self, 
        db: AsyncSession, 
        subscription: UserSubscription,
        notification_data: Dict[str, Any]
    ) -> None:
        """创建续费交易记录"""
        try:
            transaction = SubscriptionTransaction(
                id=str(uuid.uuid4()),
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                transaction_type=TransactionType.RENEWAL,
                amount=subscription.plan.price,
                currency=subscription.plan.currency,
                google_play_purchase_token=subscription.google_play_purchase_token,
                status="COMPLETED",
                transaction_time=datetime.now(timezone.utc),
                extra_data={"notification_data": notification_data}
            )
            
            db.add(transaction)
            logger.info(f"创建续费交易记录成功 - 订阅: {subscription.id}")
            
        except Exception as e:
            logger.error(f"创建续费交易记录失败: {str(e)}")
            raise

    async def handle_refund(
        self,
        db: AsyncSession,
        subscription: UserSubscription,
        refund_data: Dict[str, Any]
    ) -> None:
        """处理退款逻辑"""
        try:
            # 更新订阅状态为退款
            subscription.status = SubscriptionStatus.REFUNDED
            subscription.auto_renew = False
            
            # 设置结束时间为当前时间（立即生效）
            subscription.end_date = datetime.now(timezone.utc)
            
            # 创建退款交易记录
            refund_amount = refund_data.get("amount") or subscription.plan.price
            
            transaction = SubscriptionTransaction(
                id=str(uuid.uuid4()),
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                transaction_type=TransactionType.REFUND,
                amount=-abs(refund_amount),  # 退款金额为负数
                currency=subscription.plan.currency,
                google_play_purchase_token=subscription.google_play_purchase_token,
                google_play_order_id=subscription.google_play_order_id,
                status="COMPLETED",
                transaction_time=datetime.now(timezone.utc),
                extra_data={"refund_data": refund_data}
            )
            
            db.add(transaction)
            
            # 更新订阅的元数据
            extra_data = subscription.extra_data or {}
            extra_data["refund_info"] = {
                "refunded_at": datetime.now(timezone.utc).isoformat(),
                "refund_amount": refund_amount,
                "refund_data": refund_data
            }
            subscription.extra_data = self._make_json_serializable(extra_data)
            
            await db.commit()
            
            logger.info(f"退款处理成功 - 订阅: {subscription.id}, 金额: {refund_amount}")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"退款处理失败: {str(e)}")
            raise

    async def process_google_play_refund_notification(
        self,
        db: AsyncSession,
        notification_data: Dict[str, Any]
    ) -> bool:
        """处理Google Play退款通知"""
        try:
            # 解析退款通知数据
            one_time_product_notification = notification_data.get("oneTimeProductNotification")
            subscription_notification = notification_data.get("subscriptionNotification")
            
            if subscription_notification:
                purchase_token = subscription_notification.get("purchaseToken")
                notification_type = subscription_notification.get("notificationType")
                
                # Google Play通知类型14通常表示退款
                if notification_type == 14:  # SUBSCRIPTION_REFUNDED
                    # 查找对应的订阅记录
                    result = await db.execute(
                        select(UserSubscription)
                        .options(selectinload(UserSubscription.plan))
                        .where(UserSubscription.google_play_purchase_token == purchase_token)
                    )
                    subscription = result.scalar_one_or_none()
                    
                    if subscription:
                        await self.handle_refund(db, subscription, notification_data)
                        return True
                    else:
                        logger.warning(f"未找到对应的订阅记录用于退款: {purchase_token}")
                        
            elif one_time_product_notification:
                # 处理一次性产品退款
                purchase_token = one_time_product_notification.get("purchaseToken")
                notification_type = one_time_product_notification.get("notificationType")
                
                if notification_type == 3:  # ONE_TIME_PRODUCT_CANCELED (可能包含退款)
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
        reason: str = "manual_refund"
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
                "processed_by": "admin"
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
                logger.warning(f"无法识别的价格格式: {price_micros}, 类型: {type(price_micros)}")
                return 0.0
            
            # 转换为实际金额（微单位除以1,000,000）
            return price_int / 1_000_000
            
        except (ValueError, TypeError) as e:
            logger.error(f"价格转换失败: {price_micros}, 错误: {str(e)}")
            return 0.0

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
            return {key: self._make_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, tuple):
            return [self._make_json_serializable(item) for item in data]
        elif hasattr(data, '__dict__'):
            # 处理自定义对象
            return self._make_json_serializable(data.__dict__)
        else:
            # 基本数据类型（str, int, float, bool, None）
            return data


# 全局实例
subscription_service = SubscriptionService() 