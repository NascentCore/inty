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
    val currentSubscription: CurrentSubscription? = null,//当前用户的订阅信息，null，表示没有订阅，或者已过期。结合has_ever_subscribed判断
    val has_ever_subscribed: Boolean = false,//是否之前购买过会员订阅
    val previous_plan_id: String? = null,//上次订阅的sku的id

)

/**
 * 订阅计划详情
 */
@JsonClass(generateAdapter = true)
data class SubscriptionPlan(
    val id: String? = null,
    val name: String? = null,
    val description: String? = null,
    @Json(name = "plan_type")
    val planType: String? = null,
    val price: Double? = null,
    val currency: String? = null,
    @Json(name = "google_play_product_id")
    val googlePlayProductId: String? = null,
    @Json(name = "discount_rate")
    val discountRate: Double? = null,
    val features: Map<String, Any>? = null, // 简化为Map，因为实际结构可能复杂
    @Json(name = "chat_limit_per_day")
    val chatLimitPerDay: Int? = null,
    @Json(name = "agent_creation_limit")
    val agentCreationLimit: Int? = null,
    @Json(name = "is_active")
    val isActive: Boolean? = null,
    @Json(name = "sort_order")
    val sortOrder: Int? = null,
    @Json(name = "created_at")
    val createdAt: String? = null,
    @Json(name = "updated_at")
    val updatedAt: String? = null
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
@JsonClass(generateAdapter = true)
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
    val planId: String? = null,
    @Json(name = "google_play_purchase_token")
    val googlePlayPurchaseToken: String? = null,
    @Json(name = "google_play_order_id")
    val googlePlayOrderId: String? = null,
    @Json(name = "google_play_subscription_id")
    val googlePlaySubscriptionId: String? = null,
    val status: String? = null, // "PENDING" 等状态
    @Json(name = "start_date")
    val startDate: String? = null,
    @Json(name = "end_date")
    val endDate: String? = null,
    @Json(name = "trial_end_date")
    val trialEndDate: String? = null,
    @Json(name = "auto_renew")
    val autoRenew: Boolean? = null,
    @Json(name = "extra_data")
    val extraData: Map<String, Any>? = null,
    val id: String? = null,
    @Json(name = "user_id")
    val userId: String? = null,
    val plan: SubscriptionPlan? = null,
    @Json(name = "created_at")
    val createdAt: String? = null,
    @Json(name = "updated_at")
    val updatedAt: String? = null,
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
    @Json(name = "is_verified")
    val isVerified: Boolean,
    val subscription: CurrentSubscription?,
    val message: String?,
    @Json(name = "error_code")
    val errorCode: String?
)
