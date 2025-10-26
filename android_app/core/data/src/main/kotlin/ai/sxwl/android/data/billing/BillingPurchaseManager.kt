package ai.sxwl.android.data.billing

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.SubscriptionVerifyRequest
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import android.app.Activity
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.SkuDetailsParams
import com.architecture.httplib.core.HttpResult
import com.google.android.gms.common.ConnectionResult
import com.google.android.gms.common.GoogleApiAvailability
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/* 处理购买更新：
 * 处理完整的购买生命周期，购买流程：
 * - 前置检查：验证Google Play服务可用性
 * - 查询商品：从Google Play 获取商品详情
 * - 启动流程: 打开 Google Play 购买对话框
 * - 回调处理：接收onPurchasesUpdated()回调
 * - 确认购买: 向 Google 确认购买
 * - 服务器验证：将购买资源发送到照明验证
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
        LogUtils.d("购买更新回调: 响应码=${billingResult.responseCode}")

        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                if (purchases != null && purchases.isNotEmpty()) {
                    LogUtils.i("购买成功，处理 ${purchases.size} 个购买")
                    for (purchase in purchases) {
                        handlePurchase(purchase)
// 发送购买成功事件
                        eventScope.launch { eventFlow.emit(BillingEvent.PurchaseSuccess(purchase)) }
                    }
                } else {
                    LogUtils.w("购买成功但购买列表为空")
                    showError("purchases is empty")
                }
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                LogUtils.i("用户取消购买")
// 用户取消不发送失败事件
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                LogUtils.w("Item already owned: User already has this subscription")
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
                LogUtils.w("Item not owned: User has not purchased this item")
                showError("Item not owned")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(billingResult.responseCode, "Item not owned")
                    )
                }
            }

            BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                LogUtils.w("Item unavailable: Item is not available in current region")
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
                LogUtils.e("Developer error: Please check product ID configuration, app signature, test user settings")
                showError("Developer error")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(billingResult.responseCode, "Developer error")
                    )
                }
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                LogUtils.e("Service unavailable: Google Play services temporarily unavailable")
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
                LogUtils.e("Billing unavailable: Device does not support Google Play billing")
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
                LogUtils.e("Network error: Network connection issue")
                showError("Network error")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(billingResult.responseCode, "Network error")
                    )
                }
            }

            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                LogUtils.e("Feature not supported: Current device does not support this feature")
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
                LogUtils.e("General error: An unknown error occurred")
                showError("General error")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(billingResult.responseCode, "General error")
                    )
                }
            }

            else -> {
                LogUtils.e("购买失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
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
// 调用验证订阅信息，验证成功后再更新状态
            verifySubscriptionWithServer(purchase)
        }
    }

    /** 确认购买 */
    private fun acknowledgePurchase(purchase: Purchase) {
        val acknowledgePurchaseParams =
            AcknowledgePurchaseParams.newBuilder().setPurchaseToken(purchase.purchaseToken).build()
        billingClient.acknowledgePurchase(acknowledgePurchaseParams) { billingResult ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                LogUtils.i("购买确认成功")
// 确认成功，通知购买成功事件
                eventScope.launch { eventFlow.emit(BillingEvent.PurchaseSuccess(purchase)) }
            } else {
                LogUtils.e("购买确认失败: ${billingResult.debugMessage}")
                showError("Purchase acknowledgment failed")
// 购买确认失败，回滚订阅状态
                val oldStatus = VipStatus(isSubscribed = false)
                vipStatusFlow.value = oldStatus
                BillingStorage.saveLocalVipStatus(oldStatus)
                LogUtils.w("已回滚订阅状态")

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

    /** 调用验证订阅信息 */
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

                LogUtils.d("验证订阅: productId=${verifyRequest.productId}, purchaseToken=${verifyRequest.purchaseToken}, orderId=${verifyRequest.orderId}")
// 调用验证接口
                val result = api.verifySubscription(verifyRequest)

                when (result) {
                    is HttpResult.Success -> {
                        val response = result.data
                        if (response.isVerified) {
                            LogUtils.i("✅ 订阅验证成功")
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
                            LogUtils.w("⚠️ 订阅验证失败: ${response.message}")
                            showError("Subscription verification failed: ${response.message}")
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("❌ 订阅验证失败: ${result.message}")
                        showError("Subscription verification failed: ${result.message}")
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("❌ 订阅验证异常: ${e.message}")
                showError("Subscription verification exception: ${e.message}")
            }
        }
    }

    /** 查看购买前的状态 */
    fun checkPurchasePreconditions(activity: Activity): Boolean {
// 检查Google Play服务是否可用
        val googleApiAvailability = GoogleApiAvailability.getInstance()
        val context = activity.applicationContext
        val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)

        LogUtils.d("Google Play 服务检查结果: $resultCode")

        when (resultCode) {
            ConnectionResult.SUCCESS -> {
                LogUtils.i("✅ Google Play 服务可用")
            }

            ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> {
                LogUtils.w("⚠️ Google Play 服务需要更新")
// 尝试更新 Google Play 服务
                googleApiAvailability.getErrorDialog(activity, resultCode, 1001)?.show()
                showError("Google Play Service update required")
                return false
            }

            ConnectionResult.SERVICE_DISABLED -> {
                LogUtils.e("❌ Google Play 服务被禁用")
                showError("Google Play Service disabled")
                return false
            }

            ConnectionResult.SERVICE_MISSING -> {
                LogUtils.e("❌ Google Play 服务未安装")
                showError("Google Play Service missing")
                return false
            }

            ConnectionResult.SERVICE_INVALID -> {
                LogUtils.e("❌ Google Play 服务无效")
                showError("Google Play Service invalid")
                return false
            }

            else -> {
                LogUtils.e("❌ Google Play 服务不可用: $resultCode")
                showError("Google Play Service unavailable")
                return false
            }
        }
// 查询设备是否支持设备
        if (!isBillingSupported()) {
            LogUtils.e("❌ 设备不支持 Google Play 计费")
            showError("Google Play billing isn't supported on this device")
            return false
        }

        return true
    }

    /**查询设备是否支持电信*/
    private fun isBillingSupported(): Boolean {
        return try {
            val billingResult =
                billingClient.isFeatureSupported(BillingClient.FeatureType.SUBSCRIPTIONS)
            val isSupported = billingResult.responseCode == BillingClient.BillingResponseCode.OK
            LogUtils.d("设备计费支持检查: $isSupported (响应码: ${billingResult.responseCode}), 详情: ${billingResult.debugMessage}")
            if (!isSupported) {
                showError("Billing feature not supported on this device")
            }
            isSupported
        } catch (e: Exception) {
            LogUtils.e("检查计费支持时出错: ${e.message}")
            showError("Error checking billing support: ${e.message}")
            false
        }
    }

    /** 启动购买流程 */
    fun launchBillingFlow(activity: Activity, productId: String) {
//查询购买前条件
        if (!checkPurchasePreconditions(activity)) {
            showError("Purchase preconditions check failed")
            return
        }

        LogUtils.i("开始启动购买流程，商品ID: $productId")
// 执行购买流程
        launchBillingFlowInternal(activity, productId)
    }

    /** 内部购买流程实现 */
    private fun launchBillingFlowInternal(activity: Activity, productId: String) {
// 查询商品详情（使用SkuDetails API）
        val params =
            SkuDetailsParams.newBuilder()
                .setSkusList(listOf(productId))
                .setType(BillingClient.SkuType.SUBS)
                .build()

        billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
            LogUtils.d("查询商品详情结果: 响应码=${billingResult.responseCode}")

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    skuDetailsList?.firstOrNull()?.let { skuDetails ->
                        LogUtils.i("✅ 找到商品详情: ${skuDetails.sku}, 标题: ${skuDetails.title}, 价格: ${skuDetails.price} ${skuDetails.priceCurrencyCode}")
// 使用 SkuDetails 启动购买流程
                        val billingFlowParams =
                            BillingFlowParams.newBuilder().setSkuDetails(skuDetails).build()
                        val launchResult =
                            billingClient.launchBillingFlow(activity, billingFlowParams)
                        LogUtils.i("✅ 购买流程启动结果: $launchResult")
                    } ?: run {
                        LogUtils.e("❌ 未找到商品详情: $productId")
                        showError("Product details not found: $productId")
                    }
                }

                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    LogUtils.e("商品ID: $productId ❌ 开发者错误 (12): 请检查商品ID配置、应用签名、测试用户设置")
                    showError("Developer error: Please check product ID configuration, app signature, test user settings")
                }

                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    LogUtils.e("❌ 服务不可用: Google Play 服务暂时不可用")
                    showError("Service unavailable: Google Play services temporarily unavailable")
                }

                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    LogUtils.e("❌ 计费不可用: 设备不支持 Google Play 计费")
                    showError("Billing unavailable: Device does not support Google Play billing")
                }

                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    LogUtils.w("❌ 商品不可用: 商品在当前地区不可用")
                    showError("Item unavailable: Item is not available in current region")
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    LogUtils.e("❌ 网络错误: 网络连接问题")
                    showError("Network error: Network connection issue")
                }

                else -> {
                    LogUtils.e("❌ 查询商品详情失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
                    showError("Query product details failed: ${billingResult.debugMessage}")
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
