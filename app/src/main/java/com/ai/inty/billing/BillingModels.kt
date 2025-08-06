package com.ai.inty.billing

/**
 * 订阅状态数据类
 */
data class VipStatus(
    val isSubscribed: Boolean,
    val subscriptionId: String? = null,
    val purchaseTime: Long = 0L,
    val expiryTime: Long = 0L,
)

/**
 * 计费事件
 */
sealed class BillingEvent {
    object Connected : BillingEvent()
    object Disconnected : BillingEvent()
    data class PurchaseSuccess(val purchase: com.android.billingclient.api.Purchase) :
        BillingEvent()

    data class PurchaseFailed(val code: Int, val message: String) : BillingEvent()
    data class SkuDetailsQueryFailed(val code: Int, val message: String) : BillingEvent()
}

/**
 * 会员计划数据类
 */
data class VipPlan(
    val googleProductId: String,
    val discountRate: Double,
    val name: String,
    val planType: String,
    val description: String,
    val price: String = "-", // 价格，初始为占位符
    val originalPrice: String = "-", // 原价
    val currencyCode: String = "", // 货币代码
    val priceAmountMicros: Long = 0L, // 价格金额（微秒）
) 
