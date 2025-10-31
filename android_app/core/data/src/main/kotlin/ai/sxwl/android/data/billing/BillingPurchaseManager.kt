package ai.sxwl.android.data.billing

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.SubscriptionVerifyRequest
import ai.sxwl.android.utils.LogUtils
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
        LogUtils.d("Billing 购买更新回调: 响应码=${billingResult.responseCode}")

        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                if (purchases != null && purchases.isNotEmpty()) {
                    LogUtils.i("Billing 购买成功，处理 ${purchases.size} 个购买")
                    for (purchase in purchases) {
                        handlePurchase(purchase)
                        // 发送购买成功事件
                        eventScope.launch { eventFlow.emit(BillingEvent.PurchaseSuccess(purchase)) }
                    }
                } else {
                    LogUtils.w("Billing 购买成功但购买列表为空")
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.ShowError(
                                BillingErrorCode.PURCHASES_EMPTY
                            )
                        )
                    }
                }
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                LogUtils.i("Billing 用户取消购买")
                // 用户取消不发送失败事件
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                LogUtils.w("Billing Item already owned: User already has this subscription")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.ITEM_ALREADY_OWNED,
                            billingResult.responseCode,
                            "Item already owned"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                LogUtils.w("Billing Item not owned: User has not purchased this item")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.ITEM_NOT_OWNED,
                            billingResult.responseCode,
                            "Item not owned"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                LogUtils.w("Billing Item unavailable: Item is not available in current region")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.ITEM_UNAVAILABLE,
                            billingResult.responseCode,
                            "Item is not available in current region"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                LogUtils.e(
                    "Billing Developer error: Please check product ID configuration, app signature, test user settings"
                )
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.DEVELOPER_ERROR,
                            billingResult.responseCode,
                            "Developer error"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                LogUtils.e("Billing Service unavailable: Google Play services temporarily unavailable")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.SERVICE_UNAVAILABLE,
                            billingResult.responseCode,
                            "Service unavailable"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                LogUtils.e("Billing Billing unavailable: Device does not support Google Play billing")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.BILLING_NOT_SUPPORTED,
                            billingResult.responseCode,
                            "Device does not support Google Play billing"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                LogUtils.e("Billing Network error: Network connection issue")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.NETWORK_ERROR,
                            billingResult.responseCode,
                            "Network error"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                LogUtils.e("Billing Feature not supported: Current device does not support this feature")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.BILLING_FEATURE_NOT_SUPPORTED,
                            billingResult.responseCode,
                            "Feature not supported"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.ERROR -> {
                LogUtils.e("Billing General error: An unknown error occurred")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.UNKNOWN_ERROR,
                            billingResult.responseCode,
                            "General error"
                        )
                    )
                }
            }

            else -> {
                LogUtils.e(
                    "Billing 购买失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})"
                )
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.PURCHASE_FAILED,
                            billingResult.responseCode,
                            billingResult.debugMessage
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
                LogUtils.i("Billing 购买确认成功")
                // 确认成功，通知购买成功事件
                eventScope.launch { eventFlow.emit(BillingEvent.PurchaseSuccess(purchase)) }
            } else {
                LogUtils.e("Billing 购买确认失败: ${billingResult.debugMessage}")

                // 购买确认失败，回滚订阅状态
                val oldStatus = VipStatus(isSubscribed = false)
                vipStatusFlow.value = oldStatus
                BillingStorage.saveLocalVipStatus(oldStatus)
                LogUtils.w("Billing 已回滚订阅状态")

                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.PURCHASE_ACKNOWLEDGMENT_FAILED,
                            billingResult.responseCode,
                            billingResult.debugMessage
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

                LogUtils.d(
                    "Billing 验证订阅: productId=${verifyRequest.productId}, purchaseToken=${verifyRequest.purchaseToken}, orderId=${verifyRequest.orderId}"
                )

                // 调用验证接口
                val result = api.verifySubscription(verifyRequest)

                when (result) {
                    is HttpResult.Success -> {
                        val response = result.data
                        if (response.isVerified) {
                            LogUtils.i("Billing ✅ 订阅验证成功")
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
                            LogUtils.w("Billing ⚠️ 订阅验证失败: ${response.message}")
                            eventScope.launch {
                                eventFlow.emit(
                                    BillingEvent.ShowError(
                                        BillingErrorCode.SUBSCRIPTION_VERIFICATION_FAILED,
                                        response.message
                                    )
                                )
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("Billing ❌ 订阅验证失败: ${result.message}")
                        eventScope.launch {
                            eventFlow.emit(
                                BillingEvent.ShowError(
                                    BillingErrorCode.SUBSCRIPTION_VERIFICATION_FAILED,
                                    result.message
                                )
                            )
                        }
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("Billing ❌ 订阅验证异常: ${e.message}")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.ShowError(
                            BillingErrorCode.SUBSCRIPTION_VERIFICATION_EXCEPTION,
                            e.message
                        )
                    )
                }
            }
        }
    }

    /** 检查购买前的状态 */
    fun checkPurchasePreconditions(activity: Activity): Boolean {
        // 检查 Google Play 服务是否可用
        val googleApiAvailability = GoogleApiAvailability.getInstance()
        val context = activity.applicationContext
        val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)

        LogUtils.d("Billing Google Play 服务检查结果: $resultCode")

        when (resultCode) {
            ConnectionResult.SUCCESS -> {
                LogUtils.i("Billing ✅ Google Play 服务可用")
            }

            ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> {
                LogUtils.w("Billing ⚠️ Google Play 服务需要更新")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.GooglePlayServiceError(
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_UPDATE_REQUIRED,
                            resultCode,
                            1001
                        )
                    )
                }
                return false
            }

            ConnectionResult.SERVICE_DISABLED -> {
                LogUtils.e("Billing ❌ Google Play 服务被禁用")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.ShowError(
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_DISABLED
                        )
                    )
                }
                return false
            }

            ConnectionResult.SERVICE_MISSING -> {
                LogUtils.e("Billing ❌ Google Play 服务未安装")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.ShowError(
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_MISSING
                        )
                    )
                }
                return false
            }

            ConnectionResult.SERVICE_INVALID -> {
                LogUtils.e("Billing ❌ Google Play 服务无效")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.ShowError(
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_INVALID
                        )
                    )
                }
                return false
            }

            else -> {
                LogUtils.e("Billing ❌ Google Play 服务不可用: $resultCode")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.ShowError(
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_UNAVAILABLE
                        )
                    )
                }
                return false
            }
        }

        // 检查设备是否支持计费
        if (!isBillingSupported()) {
            LogUtils.e("Billing ❌ 设备不支持 Google Play 计费")
            eventScope.launch {
                eventFlow.emit(
                    BillingEvent.ShowError(
                        BillingErrorCode.BILLING_NOT_SUPPORTED
                    )
                )
            }
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
            LogUtils.d(
                "Billing 设备计费支持检查: $isSupported (响应码: ${billingResult.responseCode}), 详情: ${billingResult.debugMessage}"
            )
            if (!isSupported) {
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.ShowError(
                            BillingErrorCode.BILLING_FEATURE_NOT_SUPPORTED
                        )
                    )
                }
            }
            isSupported
        } catch (e: Exception) {
            LogUtils.e("Billing 检查计费支持时出错: ${e.message}")
            eventScope.launch {
                eventFlow.emit(
                    BillingEvent.ShowError(
                        BillingErrorCode.BILLING_SUPPORT_CHECK_ERROR,
                        e.message
                    )
                )
            }
            false
        }
    }

    /** 启动购买流程 */
    fun launchBillingFlow(activity: Activity, productId: String) {
        // 检查购买前条件
        if (!checkPurchasePreconditions(activity)) {
            eventScope.launch {
                eventFlow.emit(
                    BillingEvent.ShowError(
                        BillingErrorCode.PURCHASE_PRECONDITIONS_CHECK_FAILED
                    )
                )
            }
            return
        }

        LogUtils.i("Billing 开始启动购买流程，商品ID: $productId")

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

        LogUtils.i("Billing [购买流程] 开始查询商品详情，商品ID: $productId")

        billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
            LogUtils.i("Billing [购买流程] 查询商品详情结果: 响应码=${billingResult.responseCode}, 详情=${billingResult.debugMessage}")

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    skuDetailsList?.firstOrNull()?.let { skuDetails ->
                        LogUtils.i(
                            "Billing [购买流程] ✅ 找到商品详情:\n" +
                                    "  商品ID: ${skuDetails.sku}\n" +
                                    "  标题: ${skuDetails.title}\n" +
                                    "  描述: ${skuDetails.description}\n" +
                                    "  原始价格: ${skuDetails.price}\n" +
                                    "  货币代码: ${skuDetails.priceCurrencyCode}\n" +
                                    "  价格微单位: ${skuDetails.priceAmountMicros}\n" +
                                    "  价格周期: ${skuDetails.subscriptionPeriod}"
                        )

                        // 使用 SkuDetails 启动购买流程
                        val billingFlowParams =
                            BillingFlowParams.newBuilder().setSkuDetails(skuDetails).build()
                        val launchResult =
                            billingClient.launchBillingFlow(activity, billingFlowParams)
                        LogUtils.i("Billing ✅ 购买流程启动结果: $launchResult")
                    }
                        ?: run {
                            LogUtils.e("Billing ❌ 未找到商品详情: $productId")
                            eventScope.launch {
                                eventFlow.emit(
                                    BillingEvent.SkuDetailsQueryFailed(
                                        BillingErrorCode.PRODUCT_DETAILS_NOT_FOUND,
                                        BillingClient.BillingResponseCode.OK,
                                        productId
                                    )
                                )
                            }
                        }
                }

                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    LogUtils.e("Billing 商品ID: $productId ❌ 开发者错误 (12): 请检查商品ID配置、应用签名、测试用户设置")
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.DEVELOPER_ERROR,
                                billingResult.responseCode,
                                "Please check product ID configuration, app signature, test user settings"
                            )
                        )
                    }
                }

                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    LogUtils.e("Billing ❌ 服务不可用: Google Play 服务暂时不可用")
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.SERVICE_UNAVAILABLE,
                                billingResult.responseCode,
                                "Google Play services temporarily unavailable"
                            )
                        )
                    }
                }

                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    LogUtils.e("Billing ❌ 计费不可用: 设备不支持 Google Play 计费")
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.BILLING_NOT_SUPPORTED,
                                billingResult.responseCode,
                                "Device does not support Google Play billing"
                            )
                        )
                    }
                }

                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    LogUtils.w("Billing ❌ 商品不可用: 商品在当前地区不可用")
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.ITEM_UNAVAILABLE,
                                billingResult.responseCode,
                                "Item is not available in current region"
                            )
                        )
                    }
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    LogUtils.e("Billing ❌ 网络错误: 网络连接问题")
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.NETWORK_ERROR,
                                billingResult.responseCode,
                                "Network connection issue"
                            )
                        )
                    }
                }

                else -> {
                    LogUtils.e(
                        "Billing ❌ 查询商品详情失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})"
                    )
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.PRODUCT_DETAILS_QUERY_FAILED,
                                billingResult.responseCode,
                                billingResult.debugMessage
                            )
                        )
                    }
                }
            }
        }
    }
}
