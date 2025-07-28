import enum
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import (JSON, Boolean, Column, DateTime, Enum, Float,
                        ForeignKey, Integer, String, Text)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class SubscriptionPlanType(str, enum.Enum):
    """订阅计划类型"""
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class SubscriptionStatus(str, enum.Enum):
    """订阅状态"""
    ACTIVE = "ACTIVE"  # 活跃
    EXPIRED = "EXPIRED"  # 过期
    CANCELLED = "CANCELLED"  # 取消
    PENDING = "PENDING"  # 待验证
    REFUNDED = "REFUNDED"  # 退款
    GRACE_PERIOD = "GRACE_PERIOD"  # 宽限期
    PAUSED = "PAUSED"  # 暂停


class TransactionType(str, enum.Enum):
    """交易类型"""
    PURCHASE = "PURCHASE"  # 购买
    RENEWAL = "RENEWAL"  # 续费
    UPGRADE = "UPGRADE"  # 升级
    DOWNGRADE = "DOWNGRADE"  # 降级
    REFUND = "REFUND"  # 退款
    CANCEL = "CANCEL"  # 取消


class SubscriptionPlan(Base):
    """订阅计划表"""
    __tablename__ = "subscription_plans"

    id = Column(String, primary_key=True, index=True, comment="计划ID")
    name = Column(String, nullable=False, comment="计划名称")
    description = Column(Text, comment="计划描述")
    plan_type = Column(Enum(SubscriptionPlanType), nullable=False, comment="计划类型")
    price = Column(Float, nullable=False, comment="价格")
    currency = Column(String, default="USD", comment="货币")
    google_play_product_id = Column(String, unique=True, nullable=False, comment="Google Play产品ID")
    discount_rate = Column(Float, default=1.0, nullable=False, comment="价格折扣率，范围0-1，1表示无折扣")
    
    # 权益配置
    features = Column(JSON, default=dict, comment="功能权益配置")
    chat_limit_per_day = Column(Integer, default=-1, comment="每日聊天次数限制，-1为无限制")
    agent_creation_limit = Column(Integer, default=6, comment="Agent创建数量限制")
    background_generation_limit_per_day = Column(Integer, default=3, comment="每日背景图生成次数限制，-1为无限制")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'), comment="更新时间")
    
    # 关系
    user_subscriptions = relationship("UserSubscription", back_populates="plan")


class UserSubscription(Base):
    """用户订阅记录表"""
    __tablename__ = "user_subscriptions"

    id = Column(String, primary_key=True, index=True, comment="订阅记录ID")
    user_id = Column(String, ForeignKey("users.id"), nullable=False, comment="用户ID")
    plan_id = Column(String, ForeignKey("subscription_plans.id"), nullable=False, comment="订阅计划ID")
    
    # Google Play相关
    google_play_purchase_token = Column(String, unique=True, comment="Google Play购买令牌")
    google_play_order_id = Column(String, comment="Google Play订单ID")
    google_play_subscription_id = Column(String, comment="Google Play订阅ID")
    
    # 订阅状态
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING, comment="订阅状态")
    
    # 时间相关
    start_date = Column(DateTime(timezone=True), comment="开始时间")
    end_date = Column(DateTime(timezone=True), comment="结束时间")
    trial_end_date = Column(DateTime(timezone=True), comment="试用结束时间")
    
    # 自动续费
    auto_renew = Column(Boolean, default=True, comment="是否自动续费")
    
    # 额外信息
    extra_data = Column(JSON, default=dict, comment="额外元数据")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'), comment="更新时间")
    
    # 关系
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="user_subscriptions")
    transactions = relationship("SubscriptionTransaction", back_populates="subscription")


class SubscriptionTransaction(Base):
    """订阅交易记录表"""
    __tablename__ = "subscription_transactions"

    id = Column(String, primary_key=True, index=True, comment="交易记录ID")
    subscription_id = Column(String, ForeignKey("user_subscriptions.id"), nullable=False, comment="订阅记录ID")
    user_id = Column(String, ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 交易信息
    transaction_type = Column(Enum(TransactionType), nullable=False, comment="交易类型")
    amount = Column(Float, nullable=False, comment="交易金额")
    currency = Column(String, default="USD", comment="货币")
    
    # Google Play相关
    google_play_purchase_token = Column(String, comment="Google Play购买令牌")
    google_play_order_id = Column(String, comment="Google Play订单ID")
    google_play_transaction_id = Column(String, comment="Google Play交易ID")
    
    # 状态
    status = Column(String, default="PENDING", comment="交易状态")
    
    # 时间戳
    transaction_time = Column(DateTime(timezone=True), comment="交易时间")
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'), comment="更新时间")
    
    # 额外信息
    extra_data = Column(JSON, default=dict, comment="额外元数据")
    
    # 关系
    subscription = relationship("UserSubscription", back_populates="transactions")
    user = relationship("User", back_populates="subscription_transactions")


class SubscriptionUsage(Base):
    """订阅使用记录表"""
    __tablename__ = "subscription_usage"

    id = Column(String, primary_key=True, index=True, comment="使用记录ID")
    user_id = Column(String, ForeignKey("users.id"), nullable=False, comment="用户ID")
    subscription_id = Column(String, ForeignKey("user_subscriptions.id"), comment="订阅记录ID")
    
    # 使用信息
    usage_type = Column(String, nullable=False, comment="使用类型（如chat、agent_creation等）")
    usage_date = Column(DateTime(timezone=True), nullable=False, comment="使用日期")
    usage_count = Column(Integer, default=1, comment="使用次数")
    
    # 额外信息
    extra_data = Column(JSON, default=dict, comment="额外元数据")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), comment="创建时间")
    
    # 关系
    user = relationship("User", back_populates="subscription_usage")
    subscription = relationship("UserSubscription") 