from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.subscription import (
    SubscriptionPlanType,
    SubscriptionStatus,
    TransactionType,
)


class SubscriptionPlanBase(BaseModel):
    """订阅计划基础模型"""

    name: str = Field(..., description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")
    plan_type: SubscriptionPlanType = Field(..., description="计划类型")
    price: float = Field(..., description="价格")
    currency: str = Field("USD", description="货币")
    google_play_product_id: str = Field(..., description="Google Play产品ID")
    discount_rate: float = Field(
        1.0, description="价格折扣率，范围0-1，1表示无折扣"
    )
    features: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="功能权益配置"
    )
    chat_limit_per_day: int = Field(
        -1, description="每日聊天次数限制，-1为无限制"
    )
    agent_creation_limit: int = Field(6, description="Agent创建数量限制")
    background_generation_limit_per_day: int = Field(
        3, description="每日背景图生成次数限制，-1为无限制"
    )
    is_active: bool = Field(True, description="是否激活")
    sort_order: int = Field(0, description="排序顺序")


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """创建订阅计划"""

    request_id: Optional[str] = None


class SubscriptionPlanUpdate(BaseModel):
    """更新订阅计划"""

    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    discount_rate: Optional[float] = None
    features: Optional[Dict[str, Any]] = None
    chat_limit_per_day: Optional[int] = None
    agent_creation_limit: Optional[int] = None
    background_generation_limit_per_day: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    request_id: Optional[str] = None


class SubscriptionPlan(SubscriptionPlanBase):
    """订阅计划响应模型"""

    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserSubscriptionBase(BaseModel):
    """用户订阅基础模型"""

    plan_id: str = Field(..., description="订阅计划ID")
    google_play_purchase_token: Optional[str] = Field(
        None, description="Google Play购买令牌"
    )
    google_play_order_id: Optional[str] = Field(
        None, description="Google Play订单ID"
    )
    google_play_subscription_id: Optional[str] = Field(
        None, description="Google Play订阅ID"
    )
    status: SubscriptionStatus = Field(
        SubscriptionStatus.PENDING, description="订阅状态"
    )
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")
    trial_end_date: Optional[datetime] = Field(None, description="试用结束时间")
    auto_renew: bool = Field(True, description="是否自动续费")
    extra_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="额外元数据"
    )


class UserSubscriptionCreate(UserSubscriptionBase):
    """创建用户订阅"""

    request_id: Optional[str] = None


class UserSubscriptionUpdate(BaseModel):
    """更新用户订阅"""

    status: Optional[SubscriptionStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    extra_data: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class UserSubscription(UserSubscriptionBase):
    """用户订阅响应模型"""

    id: str
    user_id: str
    plan: Optional[SubscriptionPlan] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriptionTransactionBase(BaseModel):
    """订阅交易基础模型"""

    transaction_type: TransactionType = Field(..., description="交易类型")
    amount: float = Field(..., description="交易金额")
    currency: str = Field("USD", description="货币")
    google_play_purchase_token: Optional[str] = Field(
        None, description="Google Play购买令牌"
    )
    google_play_order_id: Optional[str] = Field(
        None, description="Google Play订单ID"
    )
    google_play_transaction_id: Optional[str] = Field(
        None, description="Google Play交易ID"
    )
    status: str = Field("PENDING", description="交易状态")
    transaction_time: Optional[datetime] = Field(None, description="交易时间")
    extra_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="额外元数据"
    )


class SubscriptionTransactionCreate(SubscriptionTransactionBase):
    """创建订阅交易"""

    subscription_id: str = Field(..., description="订阅记录ID")
    user_id: str = Field(..., description="用户ID")
    request_id: Optional[str] = None


class SubscriptionTransaction(SubscriptionTransactionBase):
    """订阅交易响应模型"""

    id: str
    subscription_id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriptionUsageBase(BaseModel):
    """订阅使用基础模型"""

    usage_type: str = Field(..., description="使用类型")
    usage_date: datetime = Field(..., description="使用日期")
    usage_count: int = Field(1, description="使用次数")
    extra_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="额外元数据"
    )


class SubscriptionUsageCreate(SubscriptionUsageBase):
    """创建订阅使用记录"""

    user_id: str = Field(..., description="用户ID")
    subscription_id: Optional[str] = Field(None, description="订阅记录ID")
    request_id: Optional[str] = None


class SubscriptionUsage(SubscriptionUsageBase):
    """订阅使用响应模型"""

    id: str
    user_id: str
    subscription_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Google Play相关的请求模型
class GooglePlayPurchaseRequest(BaseModel):
    """Google Play购买请求"""

    product_id: str = Field(..., description="产品ID")
    purchase_token: str = Field(..., description="购买令牌")
    order_id: Optional[str] = Field(None, description="订单ID")
    subscription_id: Optional[str] = Field(None, description="订阅ID")
    request_id: Optional[str] = None


class GooglePlayWebhookRequest(BaseModel):
    """Google Play Webhook请求"""

    version: str = Field(..., description="版本")
    packageName: str = Field(..., description="包名")
    eventTimeMillis: str = Field(..., description="事件时间")
    subscriptionNotification: Optional[Dict[str, Any]] = Field(
        None, description="订阅通知"
    )
    oneTimeProductNotification: Optional[Dict[str, Any]] = Field(
        None, description="一次性产品通知"
    )
    testNotification: Optional[Dict[str, Any]] = Field(
        None, description="测试通知"
    )
    request_id: Optional[str] = None


# 订阅状态查询相关
class FeatureInfo(BaseModel):
    """权益功能信息"""

    key: str = Field(..., description="权益key")
    name: str = Field(..., description="权益名称")
    description: str = Field(..., description="权益描述")
    type: str = Field(..., description="权益类型：real/fake")
    icon: str = Field(..., description="权益图标")
    order: int = Field(..., description="排序顺序")
    enabled: bool = Field(True, description="是否启用")


class SubscriptionStatusResponse(BaseModel):
    """订阅状态响应"""

    is_subscribed: bool = Field(..., description="是否订阅")
    subscription_status: str = Field(
        ...,
        description="订阅详细状态：subscribed/subscribed_expiring/unsubscribed",
    )
    has_ever_subscribed: bool = Field(False, description="是否曾经有过订阅记录")
    subscription: Optional[UserSubscription] = Field(
        None, description="订阅信息"
    )
    plan: Optional[SubscriptionPlan] = Field(None, description="计划信息")
    remaining_days: Optional[int] = Field(None, description="剩余天数")
    will_auto_renew: bool = Field(False, description="是否会自动续费")
    chat_limit_per_day: int = Field(-1, description="每日聊天次数限制")
    total_chat_limit: Optional[int] = Field(
        None, description="总聊天次数限制（免费用户）"
    )
    chat_24h_limit: Optional[int] = Field(
        None, description="24小时内聊天次数限制（免费用户）"
    )
    guest_chat_24h_limit: Optional[int] = Field(
        None, description="24小时内聊天次数限制（游客用户）"
    )
    voice_24h_limit: Optional[int] = Field(
        None, description="24小时内语音生成次数限制"
    )
    guest_voice_24h_limit: Optional[int] = Field(
        None, description="24小时内语音生成次数限制（游客用户）"
    )
    image_gen_24h_limit: Optional[int] = Field(
        None, description="24小时内图片生成次数限制"
    )
    agent_creation_24h_limit: Optional[int] = Field(
        None, description="24小时内Agent创建数量限制"
    )
    agent_creation_limit: int = Field(
        6,
        description="Agent创建数量限制（已废弃，使用agent_creation_24h_limit）",
    )
    background_generation_limit_per_day: int = Field(
        3,
        description="每日背景图生成次数限制（已废弃，使用image_gen_24h_limit）",
    )
    features: Dict[str, Any] = Field(
        default_factory=dict, description="功能权益"
    )
    feature_list: List[FeatureInfo] = Field(
        default_factory=list, description="权益功能列表"
    )


class UsageStatisticsResponse(BaseModel):
    """使用统计响应"""

    today_chat_count: int = Field(0, description="今日聊天次数")
    today_limit: int = Field(-1, description="今日限制")
    total_chat_count: Optional[int] = Field(
        None, description="总聊天次数（免费用户）"
    )
    total_chat_limit: Optional[int] = Field(
        None, description="总聊天次数限制（免费用户）"
    )
    chat_24h_count: Optional[int] = Field(
        None, description="24小时内聊天次数（免费用户）"
    )
    chat_24h_limit: Optional[int] = Field(
        None, description="24小时内聊天次数限制（免费用户）"
    )
    agent_count: int = Field(0, description="创建的Agent数量")
    agent_limit: int = Field(6, description="Agent创建限制")
    usage_history: List[SubscriptionUsage] = Field(
        default_factory=list, description="使用历史"
    )


# 订阅计划列表响应
class SubscriptionPlansResponse(BaseModel):
    """订阅计划列表响应"""

    plans: List[SubscriptionPlan] = Field(..., description="订阅计划列表")
    current_subscription: Optional[UserSubscription] = Field(
        None, description="当前订阅"
    )
    has_ever_subscribed: bool = Field(False, description="是否曾经有过订阅记录")
    previous_plan_id: Optional[str] = Field(
        None, description="最新的订阅计划ID"
    )


# 购买验证相关
class PurchaseVerificationRequest(BaseModel):
    """购买验证请求"""

    product_id: str = Field(..., description="产品ID")
    purchase_token: str = Field(..., description="购买令牌")
    order_id: Optional[str] = Field(None, description="订单ID")
    request_id: Optional[str] = None


class PurchaseVerificationResponse(BaseModel):
    """购买验证响应"""

    # is_valid 这个名字不能用，因为 kotlin sdk 生成的 sdk 包含了这个预置名字
    # 使用 is_valid 会与其冲突。
    is_verified: bool = Field(..., description="是否有效")
    subscription: Optional[UserSubscription] = Field(
        None, description="订阅信息"
    )
    message: str = Field(..., description="验证消息")
    error_code: Optional[str] = Field(None, description="错误代码")


class RefundRequest(BaseModel):
    """退款请求"""

    subscription_id: str = Field(..., description="订阅ID")
    refund_amount: Optional[float] = Field(
        None, description="退款金额，不填写则退全款"
    )
    reason: str = Field("manual_refund", description="退款原因")
    request_id: Optional[str] = None


class RefundResponse(BaseModel):
    """退款响应"""

    success: bool = Field(..., description="是否成功")
    subscription_id: str = Field(..., description="订阅ID")
    refund_amount: float = Field(..., description="退款金额")
    message: str = Field(..., description="处理消息")
    refunded_at: Optional[datetime] = Field(None, description="退款时间")
