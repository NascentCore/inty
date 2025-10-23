package com.ai.inty.billing

import ai.sxwl.android.utils.ToastUtils
import android.app.Activity
import com.ai.inty.beans.SubscriptionVerifyRequest
import com.ai.inty.net.NetServiceMgr
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.SkuDetailsParams
import com.architecture.httplib.core.HttpResult
import com.google.android.gms.common.GoogleApiAvailability
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/* 处理购买更新：
 * 处理完整的购买生命周期，购买流程:
 * - 前置检查: 验证 Google Play 服务可用性
 * - 查询商品: 从 Google Play 获取商品详情
 * - 启动流程: 打开 Google Play 购买对话框
 * - 回调处理: 接收 onPurchasesUpdated() 回调
 * - 确认购买: 向 Google 确认购买
 * - 服务器验证: 将购买凭证发送到后端验证
 * - 更新状态: 更新本地订阅状态
*/
internal class BillingPurchaseManager(
    private val billingClient: BillingClient,
    private val eventScope: CoroutineScope,
    private val eventFlow: MutableSharedFlow<BillingEvent>,
    private val vipStatusFlow: MutableStateFlow<VipStatus>,
) {

    private val api = NetServiceMgr.getSubscriptionApi()

    /** 处理购买更新 */
    fun onPurchasesUpdated(billingResult: BillingResult, purchases: MutableList<Purchase>?) {
        EasyLog.log(
            "BillingRepository BillingPurchaseManager - 购买更新回调: 响应码=${billingResult.responseCode}"
        )

        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                if (purchases != null && purchases.isNotEmpty()) {
                    EasyLog.log(
                        "BillingRepository BillingPurchaseManager - 购买成功，处理 ${purchases.size} 个购买"
                    )
                    for (purchase in purchases) {
                        handlePurchase(purchase)
                        // 发送购买成功事件
                        eventScope.launch { eventFlow.emit(BillingEvent.PurchaseSuccess(purchase)) }
                    }
                } else {
                    EasyLog.log("BillingRepository BillingPurchaseManager - 购买成功但购买列表为空")
                    showError("purchases is empty")
                }
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                EasyLog.log("BillingRepository BillingPurchaseManager - 用户取消购买")
                //                showError("purchases USER_CANCELED")
                // 用户取消不发送失败事件
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - Item already owned: User already has this subscription"
                )
                showError("Item already owned")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "Item already owned",
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - Item not owned: User has not purchased this item"
                )
                showError("Item not owned")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(billingResult.responseCode, "Item not owned")
                    )
                }
            }

            BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - Item unavailable: Item is not available in current region"
                )
                showError("Item is not available in current region")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "Item is not available in current region",
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - Developer error: Please check product ID configuration, app signature, test user settings"
                )
                showError("Developer error")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(billingResult.responseCode, "Developer error")
                    )
                }
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - Service unavailable: Google Play services temporarily unavailable"
                )
                showError("Service unavailable")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "Service unavailable",
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - Billing unavailable: Device does not support Google Play billing"
                )
                showError("Device does not support Google Play billing")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "Device does not support Google Play billing",
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - Network error: Network connection issue"
                )
                showError("Network error")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(billingResult.responseCode, "Network error")
                    )
                }
            }

            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - Feature not supported: Current device does not support this feature"
                )
                showError("Feature not supported")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "Feature not supported",
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.ERROR -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - General error: An unknown error occurred"
                )
                showError("General error")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(billingResult.responseCode, "General error")
                    )
                }
            }

            else -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - 购买失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})"
                )
                showError("Purchase failed: ${billingResult.debugMessage}")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            billingResult.debugMessage,
                        )
                    )
                }
            }
        }
    }

    /** 处理购买 */
    private fun handlePurchase(purchase: Purchase) {
        if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
            if (!purchase.isAcknowledged) {
                acknowledgePurchase(purchase)
            }

            // 调用后端验证订阅信息，验证成功后再更新状态
            verifySubscriptionWithServer(purchase)
        }
    }

    /** 确认购买 */
    private fun acknowledgePurchase(purchase: Purchase) {
        val acknowledgePurchaseParams =
            AcknowledgePurchaseParams.newBuilder().setPurchaseToken(purchase.purchaseToken).build()
        billingClient.acknowledgePurchase(acknowledgePurchaseParams) { billingResult ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                EasyLog.log("BillingRepository BillingPurchaseManager - 购买确认成功")
                // 确认成功，通知购买成功事件
                eventScope.launch { eventFlow.emit(BillingEvent.PurchaseSuccess(purchase)) }
            } else {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager - 购买确认失败: ${billingResult.debugMessage}"
                )
                showError("Purchase acknowledgment failed")

                // 购买确认失败，回滚订阅状态
                val oldStatus = VipStatus(isSubscribed = false)
                vipStatusFlow.value = oldStatus
                BillingStorage.saveLocalVipStatus(oldStatus)
                EasyLog.log("BillingRepository BillingPurchaseManager - 已回滚订阅状态")

                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            billingResult.debugMessage,
                        )
                    )
                }
            }
        }
    }

    /** 调用后端验证订阅信息 */
    private fun verifySubscriptionWithServer(purchase: Purchase) {
        eventScope.launch {
            try {
                // 构建验证请求
                val verifyRequest =
                    SubscriptionVerifyRequest(
                        productId = purchase.products.firstOrNull() ?: "",
                        purchaseToken = purchase.purchaseToken,
                        orderId = purchase.orderId ?: "",
                    )

                EasyLog.log(
                    "BillingRepository BillingPurchaseManager 验证订阅: productId=${verifyRequest.productId}, purchaseToken=${verifyRequest.purchaseToken}, orderId=${verifyRequest.orderId}"
                )

                // 调用验证接口
                val result = api.verifySubscription(verifyRequest)

                when (result) {
                    is HttpResult.Success -> {
                        val response = result.data
                        if (response.isVerified) {
                            EasyLog.log("BillingRepository BillingPurchaseManager ✅ 订阅验证成功")
                            // 验证成功后更新状态
                            val newStatus =
                                VipStatus(
                                    isSubscribed = true,
                                    subscriptionId = purchase.products.firstOrNull(),
                                    purchaseTime = purchase.purchaseTime,
                                )
                            vipStatusFlow.value = newStatus
                            BillingStorage.saveLocalVipStatus(newStatus)
                        } else {
                            EasyLog.log(
                                "BillingRepository BillingPurchaseManager ⚠️ 订阅验证失败: ${response.message}"
                            )
                            showError("Subscription verification failed: ${response.message}")
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "BillingRepository BillingPurchaseManager ❌ 订阅验证失败: ${result.message}"
                        )
                        showError("Subscription verification failed: ${result.message}")
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("BillingRepository BillingPurchaseManager ❌ 订阅验证异常: ${e.message}")
                showError("Subscription verification exception: ${e.message}")
            }
        }
    }

    /** 检查购买前的状态 */
    fun checkPurchasePreconditions(activity: Activity): Boolean {
        // 检查 Google Play 服务是否可用
        val googleApiAvailability = GoogleApiAvailability.getInstance()
        val context = activity.applicationContext
        val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)

        EasyLog.log("BillingRepository BillingPurchaseManager Google Play 服务检查结果: $resultCode")

        when (resultCode) {
            com.google.android.gms.common.ConnectionResult.SUCCESS -> {
                EasyLog.log("BillingRepository BillingPurchaseManager ✅ Google Play 服务可用")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> {
                EasyLog.log("BillingRepository BillingPurchaseManager ⚠️ Google Play 服务需要更新")
                // 尝试更新 Google Play 服务
                googleApiAvailability.getErrorDialog(activity, resultCode, 1001)?.show()
                showError("Google Play Service update required")
                return false
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_DISABLED -> {
                EasyLog.log("BillingRepository BillingPurchaseManager ❌ Google Play 服务被禁用")
                showError("Google Play Service disabled")
                return false
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_MISSING -> {
                EasyLog.log("BillingRepository BillingPurchaseManager ❌ Google Play 服务未安装")
                showError("Google Play Service missing")
                return false
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_INVALID -> {
                EasyLog.log("BillingRepository BillingPurchaseManager ❌ Google Play 服务无效")
                showError("Google Play Service invalid")
                return false
            }

            else -> {
                EasyLog.log(
                    "BillingRepository BillingPurchaseManager ❌ Google Play 服务不可用: $resultCode"
                )
                showError("Google Play Service unavailable")
                return false
            }
        }

        // 检查设备是否支持计费
        if (!isBillingSupported()) {
            EasyLog.log("BillingRepository BillingPurchaseManager ❌ 设备不支持 Google Play 计费")
            showError("Google Play billing isn't supported on this device")
            return false
        }

        return true
    }

    /** 检查设备是否支持计费 */
    private fun isBillingSupported(): Boolean {
        return try {
            val billingResult =
                billingClient.isFeatureSupported(BillingClient.FeatureType.SUBSCRIPTIONS)
            val isSupported = billingResult.responseCode == BillingClient.BillingResponseCode.OK
            EasyLog.log(
                "BillingRepository BillingPurchaseManager 设备计费支持检查: $isSupported (响应码: ${billingResult.responseCode})"
            )
            EasyLog.log(
                "BillingRepository BillingPurchaseManager 计费支持检查详情: ${billingResult.debugMessage}"
            )
            if (!isSupported) {
                showError("Billing feature not supported on this device")
            }
            isSupported
        } catch (e: Exception) {
            EasyLog.log("BillingRepository BillingPurchaseManager 检查计费支持时出错: ${e.message}")
            showError("Error checking billing support: ${e.message}")
            false
        }
    }

    /** 启动购买流程 */
    fun launchBillingFlow(activity: Activity, productId: String) {
        // 检查购买前条件
        if (!checkPurchasePreconditions(activity)) {
            showError("Purchase preconditions check failed")
            return
        }

        EasyLog.log("BillingRepository BillingPurchaseManager 开始启动购买流程，商品ID: $productId")

        // 执行购买流程
        launchBillingFlowInternal(activity, productId)
    }

    /** 内部购买流程实现 */
    private fun launchBillingFlowInternal(activity: Activity, productId: String) {
        // 查询商品详情（使用 SkuDetails API）
        val params =
            SkuDetailsParams.newBuilder()
                .setSkusList(listOf(productId))
                .setType(BillingClient.SkuType.SUBS)
                .build()

        billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
            EasyLog.log(
                "BillingRepository BillingPurchaseManager - 查询商品详情结果: 响应码=${billingResult.responseCode}"
            )

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    skuDetailsList?.firstOrNull()?.let { skuDetails ->
                        EasyLog.log(
                            "BillingRepository BillingPurchaseManager ✅ 找到商品详情: ${skuDetails.sku}"
                        )
                        EasyLog.log(
                            "BillingRepository BillingPurchaseManager    商品标题: ${skuDetails.title}"
                        )
                        EasyLog.log(
                            "BillingRepository BillingPurchaseManager    商品描述: ${skuDetails.description}"
                        )
                        EasyLog.log(
                            "BillingRepository BillingPurchaseManager    价格: ${skuDetails.price}"
                        )
                        EasyLog.log(
                            "BillingRepository BillingPurchaseManager    货币代码: ${skuDetails.priceCurrencyCode}"
                        )

                        // 使用 SkuDetails 启动购买流程
                        val billingFlowParams =
                            BillingFlowParams.newBuilder().setSkuDetails(skuDetails).build()
                        val launchResult =
                            billingClient.launchBillingFlow(activity, billingFlowParams)
                        EasyLog.log(
                            "BillingRepository BillingPurchaseManager ✅ 购买流程启动结果: $launchResult"
                        )
                    } ?: run {
                        EasyLog.log(
                            "BillingRepository BillingPurchaseManager ❌ 未找到商品详情: $productId"
                        )
                        showError("Product details not found: $productId")
                    }
                }

                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    EasyLog.log(
                        "BillingRepository BillingPurchaseManager 商品ID: $productId ❌ 开发者错误 (12): 请检查商品ID配置、应用签名、测试用户设置"
                    )
                    showError(
                        "Developer error: Please check product ID configuration, app signature, test user settings",
                    )
                }

                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    showError(
                        "Service unavailable: Google Play services temporarily unavailable",
                    )
                    EasyLog.log(
                        "BillingRepository BillingPurchaseManager ❌ 服务不可用: Google Play 服务暂时不可用"
                    )
                }

                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    showError(
                        "Billing unavailable: Device does not support Google Play billing",
                    )
                    EasyLog.log(
                        "BillingRepository BillingPurchaseManager ❌ 计费不可用: 设备不支持 Google Play 计费"
                    )
                }

                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    showError("Item unavailable: Item is not available in current region")
                    EasyLog.log("BillingRepository BillingPurchaseManager ❌ 商品不可用: 商品在当前地区不可用")
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    showError("Network error: Network connection issue")
                    EasyLog.log("BillingRepository BillingPurchaseManager ❌ 网络错误: 网络连接问题")
                }

                else -> {
                    showError(
                        "Query product details failed: ${billingResult.debugMessage}",
                    )
                    EasyLog.log(
                        "BillingRepository BillingPurchaseManager ❌ 查询商品详情失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})"
                    )
                }
            }
        }
    }


    private fun showError(error: String?) {
        error?.let {
            ToastUtils.showShort(error)
        }
    }
}
