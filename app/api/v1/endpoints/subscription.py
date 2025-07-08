from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json
import hmac
import hashlib

from app import schemas
from app.api import deps
from app.services.subscription_service import subscription_service
from app.schemas.subscription import (
    SubscriptionPlan,
    SubscriptionPlansResponse,
    SubscriptionStatusResponse,
    UsageStatisticsResponse,
    GooglePlayPurchaseRequest,
    GooglePlayWebhookRequest,
    PurchaseVerificationRequest,
    PurchaseVerificationResponse
)
from app.schemas.response import APIResponse
from app.core.config import settings

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
        plans = await subscription_service.get_subscription_plans(db, include_inactive=False)
        
        # 获取用户当前订阅
        current_subscription = await subscription_service.get_user_current_subscription(
            db, current_user.id
        )
        
        response = SubscriptionPlansResponse(
            plans=plans,
            current_subscription=current_subscription
        )
        
        return APIResponse.success(data=response)
        
    except Exception as e:
        logger.error(f"获取订阅计划列表失败: {str(e)}")
        return APIResponse.error(message="获取订阅计划失败")


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
        status = await subscription_service.get_user_subscription_status(db, current_user.id)
        return APIResponse.success(data=status)
        
    except Exception as e:
        logger.error(f"获取用户订阅状态失败: {str(e)}")
        return APIResponse.error(message="获取订阅状态失败")


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
        usage_stats = await subscription_service.get_user_usage_statistics(db, current_user.id)
        return APIResponse.success(data=usage_stats)
        
    except Exception as e:
        logger.error(f"获取用户使用统计失败: {str(e)}")
        return APIResponse.error(message="获取使用统计失败")


@router.post("/verify", response_model=APIResponse[PurchaseVerificationResponse])
async def verify_purchase(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    purchase_request: PurchaseVerificationRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    验证Google Play购买并创建订阅
    """
    try:
        google_play_request = GooglePlayPurchaseRequest(
            product_id=purchase_request.product_id,
            purchase_token=purchase_request.purchase_token,
            order_id=purchase_request.order_id
        )
        
        result = await subscription_service.verify_and_create_subscription(
            db, current_user.id, google_play_request
        )
        
        if result.is_valid:
            return APIResponse.success(data=result, message="购买验证成功")
        else:
            return APIResponse.error(message=result.message, data=result)
            
    except Exception as e:
        logger.error(f"验证购买失败: {str(e)}")
        return APIResponse.error(message="购买验证失败")


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
            if not signature or not verify_webhook_signature(body, signature):
                raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        # 解析请求数据
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON data")
        
        # 在后台处理通知
        background_tasks.add_task(
            _process_google_play_notification,
            db,
            data
        )
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理Google Play webhook失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _process_google_play_notification(
    db: AsyncSession,
    notification_data: Dict[str, Any]
) -> None:
    """处理Google Play通知的后台任务"""
    try:
        # 解码base64数据
        if "message" in notification_data and "data" in notification_data["message"]:
            import base64
            decoded_data = base64.b64decode(notification_data["message"]["data"])
            notification_json = json.loads(decoded_data.decode('utf-8'))
            
            # 处理订阅通知
            success = await subscription_service.handle_subscription_notification(
                db, notification_json
            )
            
            if success:
                logger.info("Google Play订阅通知处理成功")
            else:
                logger.warning("Google Play订阅通知处理失败")
                
    except Exception as e:
        logger.error(f"处理Google Play订阅通知失败: {str(e)}")


def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    """验证webhook签名"""
    try:
        if not settings.google_play.webhook_secret:
            return True
        
        expected_signature = hmac.new(
            settings.google_play.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
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
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        plan = await subscription_service.create_subscription_plan(db, plan_data)
        return APIResponse.success(data=plan, message="订阅计划创建成功")
        
    except Exception as e:
        logger.error(f"创建订阅计划失败: {str(e)}")
        return APIResponse.error(message="创建订阅计划失败")


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
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        plans = await subscription_service.get_subscription_plans(db, include_inactive)
        return APIResponse.success(data=plans)
        
    except Exception as e:
        logger.error(f"获取订阅计划列表失败: {str(e)}")
        return APIResponse.error(message="获取订阅计划失败")


@router.get("/admin/users/{user_id}/subscription", response_model=APIResponse[SubscriptionStatusResponse])
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
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        status = await subscription_service.get_user_subscription_status(db, user_id)
        return APIResponse.success(data=status)
        
    except Exception as e:
        logger.error(f"获取用户订阅状态失败: {str(e)}")
        return APIResponse.error(message="获取订阅状态失败")


@router.get("/admin/users/{user_id}/usage", response_model=APIResponse[UsageStatisticsResponse])
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
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        usage_stats = await subscription_service.get_user_usage_statistics(db, user_id)
        return APIResponse.success(data=usage_stats)
        
    except Exception as e:
        logger.error(f"获取用户使用统计失败: {str(e)}")
        return APIResponse.error(message="获取使用统计失败") 