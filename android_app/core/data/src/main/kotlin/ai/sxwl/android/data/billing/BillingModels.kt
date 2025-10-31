package ai.sxwl.android.data.billing

import com.android.billingclient.api.Purchase

/** 订阅状态数据类 */
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

/** Billing 错误码枚举 - 用于 app 模块根据错误码显示对应的 UI 提示 */
enum class BillingErrorCode {
    // 购买相关错误
    PURCHASES_EMPTY,                    // 购买列表为空
    ITEM_ALREADY_OWNED,                 // 用户已经拥有此商品
    ITEM_NOT_OWNED,                     // 用户未拥有此商品
    ITEM_UNAVAILABLE,                   // 商品在当前地区不可用
    PURCHASE_FAILED,                    // 购买失败（通用）
    PURCHASE_ACKNOWLEDGMENT_FAILED,     // 购买确认失败

    // 订阅验证相关错误
    SUBSCRIPTION_VERIFICATION_FAILED,   // 订阅验证失败
    SUBSCRIPTION_VERIFICATION_EXCEPTION, // 订阅验证异常

    // Google Play 服务相关错误
    GOOGLE_PLAY_SERVICE_UPDATE_REQUIRED, // Google Play 服务需要更新
    GOOGLE_PLAY_SERVICE_DISABLED,        // Google Play 服务被禁用
    GOOGLE_PLAY_SERVICE_MISSING,         // Google Play 服务未安装
    GOOGLE_PLAY_SERVICE_INVALID,         // Google Play 服务无效
    GOOGLE_PLAY_SERVICE_UNAVAILABLE,      // Google Play 服务不可用

    // 计费功能相关错误
    BILLING_NOT_SUPPORTED,              // 设备不支持 Google Play 计费
    BILLING_FEATURE_NOT_SUPPORTED,      // 设备不支持此计费功能

    // 服务相关错误
    SERVICE_UNAVAILABLE,                // Google Play 服务暂时不可用
    NETWORK_ERROR,                      // 网络连接错误
    DEVELOPER_ERROR,                    // 开发者错误（商品ID配置等）

    // 商品查询相关错误
    PRODUCT_DETAILS_NOT_FOUND,          // 未找到商品详情
    PRODUCT_DETAILS_QUERY_FAILED,      // 查询商品详情失败

    // 前置检查错误
    PURCHASE_PRECONDITIONS_CHECK_FAILED, // 购买前置检查失败
    BILLING_SUPPORT_CHECK_ERROR,        // 检查计费支持时出错

    // 未知错误
    UNKNOWN_ERROR,                      // 未知错误
}

/** 计费事件 */
sealed class BillingEvent {
    object Connected : BillingEvent()

    object Disconnected : BillingEvent()

    data class PurchaseSuccess(val purchase: Purchase) : BillingEvent()

    /** 购买失败事件 - 包含错误码和可选的详细消息 */
    data class PurchaseFailed(
        val errorCode: BillingErrorCode,
        val billingResponseCode: Int,
        val detailMessage: String? = null
    ) : BillingEvent()

    /** 商品详情查询失败事件 - 包含错误码和可选的详细消息 */
    data class SkuDetailsQueryFailed(
        val errorCode: BillingErrorCode,
        val billingResponseCode: Int,
        val detailMessage: String? = null
    ) : BillingEvent()

    /** 初始化失败事件 - 包含错误码和原因 */
    data class InitializationFailed(
        val errorCode: BillingErrorCode,
        val reason: String
    ) : BillingEvent()

    object AppResumed : BillingEvent()

    data class SubscriptionStatusChanged(val oldStatus: VipStatus, val newStatus: VipStatus) :
        BillingEvent()

    /** UI 错误事件 - 需要显示 toast 的错误 */
    data class ShowError(
        val errorCode: BillingErrorCode,
        val detailMessage: String? = null
    ) : BillingEvent()

    /** Google Play 服务错误 - 需要显示系统 Dialog */
    data class GooglePlayServiceError(
        val errorCode: BillingErrorCode,
        val connectionResult: Int,
        val requestCode: Int = 1001
    ) : BillingEvent()
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
