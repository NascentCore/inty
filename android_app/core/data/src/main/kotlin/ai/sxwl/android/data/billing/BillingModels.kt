package ai.sxwl.android.data.billing

import com.android.billingclient.api.Purchase

/** 订阅状态​​​​​​​数据类 */
data class VipStatus(
    val isSubscribed: Boolean, // 是否订阅中的状态
    val subscriptionId: String? = null, // 订阅的id
    val purchaseTime: Long? = null, // 购买时间的时间戳
    val expiryTime: Long? = null, // 过期时间的时间戳，
    val everSubscribed: Boolean = false, // 是否曾经订阅过
    val previous_plan_id: String? = null, // 上次订阅的sku的id
    val subscriptionStatus: String? = null,
) {
    companion object {
        const val UI_SUBSCRIBED = "SUBSCRIBED"
        const val UI_UNSUBSCRIBED = "UNSUBSCRIBED"
        const val UI_SUBSCRIBED_EXPIRE_SOON = "SUBSCRIBED_EXPIRE_SOON"
    }
}

/** 华为事件 */
sealed class BillingEvent {
    object Connected : BillingEvent()

    object Disconnected : BillingEvent()

    data class PurchaseSuccess(val purchase: Purchase) : BillingEvent()

    data class PurchaseFailed(val code: Int, val message: String) : BillingEvent()

    data class SkuDetailsQueryFailed(val code: Int, val message: String) : BillingEvent()

    data class InitializationFailed(val reason: String) : BillingEvent()

    object AppResumed : BillingEvent()

    data class SubscriptionStatusChanged(val oldStatus: VipStatus, val newStatus: VipStatus) :
        BillingEvent()
}

/** BillingRepository初始化状态 */
data class BillingInitState(
    val isInitialized: Boolean = false,
    val isConnected: Boolean = false,
    val hasGooglePlayServices: Boolean = false,
    val errorMessage: String? = null,
)

/** 会员计划数据类 */
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
