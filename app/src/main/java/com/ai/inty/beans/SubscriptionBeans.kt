package com.ai.inty.beans

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

/**
 * 订阅计划API响应
 */
@JsonClass(generateAdapter = true)
data class SubscriptionPlansResponse(
    val plans: List<SubscriptionPlan>,
    @Json(name = "current_subscription")
    val currentSubscription: CurrentSubscription?
)

/**
 * 订阅计划详情
 */
@JsonClass(generateAdapter = true)
data class SubscriptionPlan(
    val id: String,
    val name: String,
    val description: String,
    @Json(name = "plan_type")
    val planType: String,
    val price: Double,
    val currency: String,
    @Json(name = "google_play_product_id")
    val googlePlayProductId: String,
    @Json(name = "discount_rate")
    val discountRate: Double,
    val features: PlanFeatures,
    @Json(name = "chat_limit_per_day")
    val chatLimitPerDay: Int,
    @Json(name = "agent_creation_limit")
    val agentCreationLimit: Int,
    @Json(name = "is_active")
    val isActive: Boolean,
    @Json(name = "sort_order")
    val sortOrder: Int,
    @Json(name = "created_at")
    val createdAt: String,
    @Json(name = "updated_at")
    val updatedAt: String
)

/**
 * 计划功能特性
 */
@JsonClass(generateAdapter = true)
data class PlanFeatures(
    val features: List<PlanFeature>,
    @Json(name = "real_features")
    val realFeatures: List<String>,
    @Json(name = "fake_features")
    val fakeFeatures: List<String>
)

/**
 * 单个功能特性
 */
@JsonClass(generateAdapter = true)
data class PlanFeature(
    val key: String,
    val name: String,
    val description: String,
    val type: String, // "real" 或 "fake"
    val icon: String,
    val order: Int
)

/**
 * 商品数据类，包含商品的所有信息
 */
data class Product(
    val id: String,
    val name: String,
    val price: String = "-",
    val originalPrice: String = "-", // 原始价格（包含货币符号）
    val currencyCode: String = "", // 货币代码
    val priceAmountMicros: Long = 0 // 价格金额（微秒）
)

/**
 * 当前订阅信息
 */
@JsonClass(generateAdapter = true)
data class CurrentSubscription(
    @Json(name = "plan_id")
    val planId: String,
    @Json(name = "google_play_purchase_token")
    val googlePlayPurchaseToken: String,
    @Json(name = "google_play_order_id")
    val googlePlayOrderId: String,
    @Json(name = "google_play_subscription_id")
    val googlePlaySubscriptionId: String,
    val status: String, // "PENDING" 等状态
    @Json(name = "start_date")
    val startDate: String,
    @Json(name = "end_date")
    val endDate: String,
    @Json(name = "trial_end_date")
    val trialEndDate: String,
    @Json(name = "auto_renew")
    val autoRenew: Boolean,
    @Json(name = "extra_data")
    val extraData: Map<String, Any>,
    val id: String,
    @Json(name = "user_id")
    val userId: String,
    val plan: SubscriptionPlan
)

/**
 * 订阅验证请求
 */
@JsonClass(generateAdapter = true)
data class SubscriptionVerifyRequest(
    @Json(name = "product_id")
    val productId: String,
    @Json(name = "purchase_token")
    val purchaseToken: String,
    @Json(name = "order_id")
    val orderId: String
)

/**
 * 订阅验证响应
 */
@JsonClass(generateAdapter = true)
data class SubscriptionVerifyResponse(
    @Json(name = "is_valid")
    val isValid: Boolean,
    val subscription: CurrentSubscription?,
    val message: String?,
    @Json(name = "error_code")
    val errorCode: String?
)