package com.ai.inty.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.*
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object BillingManager : PurchasesUpdatedListener, BillingClientStateListener {
    private lateinit var billingClient: BillingClient
    private var isConnected = false

    // 订阅状态流
    private val _subscriptionStatus = MutableStateFlow<SubscriptionStatus>(SubscriptionStatus.NotSubscribed)
    val subscriptionStatus: StateFlow<SubscriptionStatus> = _subscriptionStatus.asStateFlow()

    // 商品信息流
    private val _skuDetails = MutableStateFlow<List<SkuDetails>>(emptyList())
    val skuDetails: StateFlow<List<SkuDetails>> = _skuDetails.asStateFlow()

    fun initialize(context: Context) {
        if (::billingClient.isInitialized) return

        // 打印设备区域和货币信息
        val locale = context.resources.configuration.locales[0]
        val currency = java.util.Currency.getInstance(locale)
        EasyLog.log("设备区域: ${locale.displayCountry} (${locale.country}), 货币: ${currency.displayName} (${currency.currencyCode})")

        billingClient = BillingClient.newBuilder(context.applicationContext)
            .setListener(this)
            .enablePendingPurchases()
            .build()

        connectToPlayBilling()
    }

    private fun connectToPlayBilling() {
        billingClient.startConnection(this)
    }

    // PurchasesUpdatedListener 实现
    override fun onPurchasesUpdated(billingResult: BillingResult, purchases: MutableList<Purchase>?) {
        if (billingResult.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
            for (purchase in purchases) {
                handlePurchase(purchase)
            }
        } else if (billingResult.responseCode == BillingClient.BillingResponseCode.USER_CANCELED) {
            EasyLog.log("用户取消购买")
        } else {
            EasyLog.log("购买失败: ${billingResult.debugMessage}")
        }
    }

    // BillingClientStateListener 实现
    override fun onBillingSetupFinished(billingResult: BillingResult) {
        if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
            isConnected = true
            EasyLog.log("BillingClient 连接成功")
            // 连接成功后查询商品信息
            querySkuDetails()
            // 查询现有订阅
            queryPurchases()
        } else {
            EasyLog.log("BillingClient 连接失败: ${billingResult.debugMessage}")
        }
    }

    override fun onBillingServiceDisconnected() {
        isConnected = false
        EasyLog.log("BillingClient 断开连接")
    }

    private fun querySkuDetails() {
        val subscriptionIds = BillingConfig.getSubscriptionIds()
        EasyLog.log("Google Play 商品查询开始, 商品ID: $subscriptionIds")
        
        if (subscriptionIds.isEmpty()) {
            EasyLog.log("商品ID列表为空，跳过查询")
            return
        }
        
        // 检查BillingClient连接状态
        if (!isConnected) {
            EasyLog.log("BillingClient 未连接，无法查询商品")
            return
        }
        
        val params = SkuDetailsParams.newBuilder()
            .setSkusList(subscriptionIds)
            .setType(BillingClient.SkuType.SUBS)
            .build()

        EasyLog.log("发送查询请求到Google Play")
        billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
            EasyLog.log("Google Play 查询结果: 响应码=${billingResult.responseCode}, 信息=${billingResult.debugMessage}")
            
            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    skuDetailsList?.let {
                        _skuDetails.value = it
                        EasyLog.log("查询成功，获取到 ${it.size} 个商品信息")
                        if (it.isNotEmpty()) {
                            it.forEach { sku ->
                                EasyLog.log("商品详情: ID=${sku.sku}, 标题=${sku.title}, 价格=${sku.price}")
                                EasyLog.log("价格详情: 金额=${sku.priceAmountMicros}, 货币=${sku.priceCurrencyCode}, 订阅期=${sku.subscriptionPeriod}")
                            }
                        } else {
                            EasyLog.log("查询成功但返回空商品列表，可能原因: 商品ID不存在或未在Google Play Console中激活")
                        }
                    } ?: run {
                        EasyLog.log("Google Play返回的商品列表为null")
                        _skuDetails.value = emptyList()
                    }
                }
                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    EasyLog.log("开发者错误 (12): 请检查商品ID配置、应用签名、测试用户设置")
                    EasyLog.log("当前查询的商品ID: $subscriptionIds")
                    _skuDetails.value = emptyList()
                }
                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    EasyLog.log("服务不可用: Google Play 服务暂时不可用")
                    _skuDetails.value = emptyList()
                }
                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    EasyLog.log("计费不可用: 设备不支持 Google Play 计费")
                    _skuDetails.value = emptyList()
                }
                BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                    EasyLog.log("商品未拥有: 用户未购买该商品")
                    _skuDetails.value = emptyList()
                }
                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    EasyLog.log("商品不可用: 商品在当前地区不可用")
                    _skuDetails.value = emptyList()
                }
                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    EasyLog.log("网络错误: 网络连接问题")
                    _skuDetails.value = emptyList()
                }
                BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                    EasyLog.log("功能不支持: 当前设备不支持此功能")
                    _skuDetails.value = emptyList()
                }
                BillingClient.BillingResponseCode.USER_CANCELED -> {
                    EasyLog.log("用户取消: 用户取消了操作")
                    _skuDetails.value = emptyList()
                }
                BillingClient.BillingResponseCode.ERROR -> {
                    EasyLog.log("一般错误: 发生了未知错误")
                    _skuDetails.value = emptyList()
                }
                else -> {
                    EasyLog.log("未知错误: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
                    _skuDetails.value = emptyList()
                }
            }
        }
    }

    private fun queryPurchases() {
        billingClient.queryPurchasesAsync(
            QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.SUBS)
                .build()
        ) { billingResult, purchasesList ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                handlePurchases(purchasesList)
            }
        }
    }

    private fun handlePurchases(purchases: List<Purchase>) {
        if (purchases.isEmpty()) {
            _subscriptionStatus.value = SubscriptionStatus.NotSubscribed
            return
        }

        for (purchase in purchases) {
            if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
                if (!purchase.isAcknowledged) {
                    acknowledgePurchase(purchase)
                }
                _subscriptionStatus.value = SubscriptionStatus.Subscribed
            } else if (purchase.purchaseState == Purchase.PurchaseState.PENDING) {
                _subscriptionStatus.value = SubscriptionStatus.Pending
            }
        }
    }

    private fun handlePurchase(purchase: Purchase) {
        if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
            if (!purchase.isAcknowledged) {
                acknowledgePurchase(purchase)
            }
            _subscriptionStatus.value = SubscriptionStatus.Subscribed
        }
    }

    private fun acknowledgePurchase(purchase: Purchase) {
        val acknowledgePurchaseParams = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        billingClient.acknowledgePurchase(acknowledgePurchaseParams) { billingResult ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                EasyLog.log("购买确认成功")
            }
        }
    }

    fun launchBillingFlow(activity: Activity, skuDetails: SkuDetails) {
        if (!isConnected) {
            EasyLog.log("BillingClient 未连接")
            return
        }

        val billingFlowParams = BillingFlowParams.newBuilder()
            .setSkuDetails(skuDetails)
            .build()

        billingClient.launchBillingFlow(activity, billingFlowParams)
    }

    fun release() {
        if (::billingClient.isInitialized) {
            billingClient.endConnection()
            isConnected = false
        }
    }
}

sealed class SubscriptionStatus {
    object NotSubscribed : SubscriptionStatus()
    object Subscribed : SubscriptionStatus()
    object Pending : SubscriptionStatus()
} 