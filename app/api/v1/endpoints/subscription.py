import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.core.config import settings
from app.models.subscription import UserSubscription
from app.schemas.response import APIResponse
from app.schemas.subscription import (
    GooglePlayPurchaseRequest,
    GooglePlayWebhookRequest,
    PurchaseVerificationRequest,
    PurchaseVerificationResponse,
    RefundRequest,
    RefundResponse,
    SubscriptionPlan,
    SubscriptionPlansResponse,
    SubscriptionStatusResponse,
    UsageStatisticsResponse,
)
from app.services.subscription_service import subscription_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/plans", response_model=APIResponse[SubscriptionPlansResponse])
async def get_subscription_plans(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取订阅计划列表
    """
    try:
        # 获取所有激活的订阅计划
        plans = await subscription_service.get_subscription_plans(
            db, include_inactive=False
        )

        # 获取用户当前订阅
        current_subscription = await subscription_service.get_user_current_subscription(
            db, current_user.id
        )

        # 获取用户历史订阅记录
        has_ever_subscribed = await subscription_service.has_ever_subscribed(
            db, current_user.id
        )

        # 将 SQLAlchemy 模型转换为 Pydantic 模型
        current_subscription_schema = None
        if current_subscription:
            current_subscription_schema = UserSubscription.model_validate(
                current_subscription
            )

        response = SubscriptionPlansResponse(
            plans=plans,
            current_subscription=current_subscription_schema,
            has_ever_subscribed=has_ever_subscribed,
        )

        return APIResponse.success(data=response)

    except Exception as e:
        logger.error(f"获取订阅计划列表失败: {str(e)}")
        return APIResponse.error(message="Failed to get subscription plans")


# TODO: Can this be removed? /plans already returns the users's subscription status.
@router.get("/status", response_model=APIResponse[SubscriptionStatusResponse])
async def get_subscription_status(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户订阅状态
    """
    try:
        status = await subscription_service.get_user_subscription_status(
            db, current_user.id
        )
        return APIResponse.success(data=status)

    except Exception as e:
        logger.error(f"获取用户订阅状态失败: {str(e)}")
        return APIResponse.error(message="Failed to get subscription status")


# TODO: Can be removed, as usage is only used for checking limits, and limits checking now is done
# on server side.
@router.get("/usage", response_model=APIResponse[UsageStatisticsResponse])
async def get_usage_statistics(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户使用统计
    """
    try:
        usage_stats = await subscription_service.get_user_usage_statistics(
            db, current_user.id
        )
        return APIResponse.success(data=usage_stats)

    except Exception as e:
        logger.error(f"获取用户使用统计失败: {str(e)}")
        return APIResponse.error(message="Failed to get usage statistics")


# This is only used for verifying the purchase on client side.
# TODO: Can it verify the restoration and cancellation?
@router.post("/verify", response_model=APIResponse[PurchaseVerificationResponse])
async def verify_purchase(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    purchase_request: PurchaseVerificationRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    验证 Google Play 购买并创建订阅
    """
    try:
        google_play_request = GooglePlayPurchaseRequest(
            product_id=purchase_request.product_id,
            purchase_token=purchase_request.purchase_token,
            order_id=purchase_request.order_id,
        )

        result = await subscription_service.verify_and_create_subscription(
            db, current_user.id, google_play_request
        )

        logger.error(f"购买验证结果: {result}")

        if result.is_valid:
            return APIResponse.success(
                data=result, message="Purchase verification successful"
            )
        else:
            return APIResponse.error(message=result.message, data=result)

    except Exception as e:
        logger.error(f"验证购买失败: {str(e)}")
        return APIResponse.error(message="Purchase verification failed")


# Handles restoration and cancellation from Google Play.
@router.post("/webhook")
async def google_play_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_async_db),
) -> Dict[str, str]:
    """
    Google Play Developer Notifications webhook
    处理订阅状态变化通知
    """
    try:
        # 获取请求体
        body = await request.body()

        # 验证webhook签名（如果配置了webhook密钥）
        if settings.google_play.webhook_secret:
            signature = request.headers.get("X-Goog-Message-Signature")
            if not signature or not _verify_webhook_signature(body, signature):
                raise HTTPException(status_code=400, detail="Invalid webhook signature")

        # 解析请求数据
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON data")

        # 日志记录 data 数据
        logger.info(f"Google Play Webhook收到数据: {data}")

        # 在后台处理通知
        background_tasks.add_task(_process_google_play_notification, db, data)

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理Google Play webhook失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _process_google_play_notification(
    db: AsyncSession, notification_data: Dict[str, Any]
) -> None:
    """处理Google Play通知的后台任务"""
    max_retries = 3
    retry_delay = 5  # 秒

    for attempt in range(max_retries):
        try:
            # 解码base64数据
            if (
                "message" in notification_data
                and "data" in notification_data["message"]
            ):
                import base64

                decoded_data = base64.b64decode(notification_data["message"]["data"])
                notification_json = json.loads(decoded_data.decode("utf-8"))

                # 记录详细的通知信息
                subscription_notification = notification_json.get(
                    "subscriptionNotification", {}
                )
                purchase_token = subscription_notification.get(
                    "purchaseToken", "unknown"
                )
                notification_type = subscription_notification.get(
                    "notificationType", "unknown"
                )

                logger.info(
                    f"处理Google Play通知 - 尝试 {attempt + 1}/{max_retries}, "
                    f"令牌: {purchase_token[:10]}..., 类型: {notification_type}"
                )

                # 处理订阅通知
                success = await subscription_service.handle_subscription_notification(
                    db, notification_json
                )

                if success:
                    logger.info(
                        f"Google Play订阅通知处理成功 - 令牌: {purchase_token[:10]}..."
                    )
                    return
                else:
                    logger.warning(
                        f"Google Play订阅通知处理失败 - 令牌: {purchase_token[:10]}..., "
                        f"尝试 {attempt + 1}/{max_retries}"
                    )

                    if attempt < max_retries - 1:
                        # 等待后重试
                        import asyncio

                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        logger.error(
                            f"Google Play订阅通知处理最终失败 - 令牌: {purchase_token[:10]}..."
                        )

        except Exception as e:
            logger.error(
                f"处理Google Play订阅通知失败: {str(e)}, 尝试 {attempt + 1}/{max_retries}"
            )
            if attempt < max_retries - 1:
                import asyncio

                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Google Play订阅通知处理最终异常失败: {str(e)}")


def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    """验证webhook签名"""
    try:
        if not settings.google_play.webhook_secret:
            return True

        expected_signature = hmac.new(
            settings.google_play.webhook_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        logger.error(f"验证webhook签名失败: {str(e)}")
        return False


# 管理员接口
@router.post("/admin/plans", response_model=APIResponse[SubscriptionPlan])
async def create_subscription_plan(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    plan_data: schemas.subscription.SubscriptionPlanCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建订阅计划（管理员接口）
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        plan = await subscription_service.create_subscription_plan(db, plan_data)
        # 将 SQLAlchemy 模型转换为 Pydantic 模型
        plan_schema = SubscriptionPlan.model_validate(plan)
        return APIResponse.success(
            data=plan_schema, message="Subscription plan created successfully"
        )

    except Exception as e:
        logger.error(f"创建订阅计划失败: {str(e)}")
        return APIResponse.error(message="Failed to create subscription plan")


@router.get("/admin/plans", response_model=APIResponse[List[SubscriptionPlan]])
async def get_all_subscription_plans(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    include_inactive: bool = False,
) -> Any:
    """
    获取所有订阅计划（管理员接口）
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        plans = await subscription_service.get_subscription_plans(db, include_inactive)
        return APIResponse.success(data=plans)

    except Exception as e:
        logger.error(f"获取订阅计划列表失败: {str(e)}")
        return APIResponse.error(message="Failed to get subscription plans")


@router.get(
    "/admin/users/{user_id}/subscription",
    response_model=APIResponse[SubscriptionStatusResponse],
)
async def get_user_subscription_status_admin(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    user_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定用户的订阅状态（管理员接口）
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        status = await subscription_service.get_user_subscription_status(db, user_id)
        return APIResponse.success(data=status)

    except Exception as e:
        logger.error(f"获取用户订阅状态失败: {str(e)}")
        return APIResponse.error(message="Failed to get subscription status")


@router.get(
    "/admin/users/{user_id}/usage", response_model=APIResponse[UsageStatisticsResponse]
)
async def get_user_usage_statistics_admin(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    user_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定用户的使用统计（管理员接口）
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        usage_stats = await subscription_service.get_user_usage_statistics(db, user_id)
        return APIResponse.success(data=usage_stats)

    except Exception as e:
        logger.error(f"获取用户使用统计失败: {str(e)}")
        return APIResponse.error(message="Failed to get usage statistics")


@router.post("/admin/refund", response_model=APIResponse[RefundResponse])
async def process_manual_refund(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    refund_request: RefundRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    手动处理退款（管理员接口）
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        success = await subscription_service.manual_refund(
            db,
            refund_request.subscription_id,
            refund_request.refund_amount,
            refund_request.reason,
        )

        if success:
            # 获取更新后的订阅信息
            result = await db.execute(
                select(UserSubscription).where(
                    UserSubscription.id == refund_request.subscription_id
                )
            )
            subscription = result.scalar_one_or_none()

            refund_info = (
                subscription.extra_data.get("refund_info", {}) if subscription else {}
            )

            response = RefundResponse(
                success=True,
                subscription_id=refund_request.subscription_id,
                refund_amount=refund_info.get("refund_amount", 0),
                message="Refund processed successfully",
                refunded_at=(
                    datetime.fromisoformat(refund_info.get("refunded_at"))
                    if refund_info.get("refunded_at")
                    else None
                ),
            )

            return APIResponse.success(
                data=response, message="Refund processed successfully"
            )
        else:
            return APIResponse.error(message="Refund processing failed")

    except Exception as e:
        logger.error(f"手动退款处理失败: {str(e)}")
        return APIResponse.error(message="Refund processing failed")
