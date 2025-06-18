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
        val params = SkuDetailsParams.newBuilder()
            .setSkusList(BillingConfig.getSubscriptionIds())
            .setType(BillingClient.SkuType.SUBS)
            .build()

        billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                skuDetailsList?.let {
                    _skuDetails.value = it
                    EasyLog.log("获取到 ${it.size} 个商品信息")
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