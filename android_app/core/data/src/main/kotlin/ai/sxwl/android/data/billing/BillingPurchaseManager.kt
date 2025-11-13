package ai.sxwl.android.data.billing

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.SubscriptionVerifyRequest
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.app.Activity
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.QueryProductDetailsParams
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
    private val plansFlow: MutableStateFlow<List<VipPlan>>,
) {

    private val api = NetServiceMgr.getSubscriptionApi()

    /** 处理购买更新 */
    fun onPurchasesUpdated(billingResult: BillingResult, purchases: MutableList<Purchase>?) {
        LogUtils.d("Billing 购买更新回调: 响应码=${billingResult.responseCode}")

        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                if (purchases != null && purchases.isNotEmpty()) {
                    LogUtils.i("Billing 购买成功，处理 ${purchases.size} 个购买")

                    // 记录所有购买的详细信息，便于调试
                    purchases.forEachIndexed { index, purchase ->
                        LogUtils.d(
                            "Billing 购买[$index]: productIds=${purchase.products}, " +
                                "purchaseToken=${purchase.purchaseToken}, orderId=${purchase.orderId}, " +
                                "purchaseState=${purchase.purchaseState}, isAcknowledged=${purchase.isAcknowledged}"
                        )
                    }

                    for (purchase in purchases) {
                        handlePurchase(purchase)
                        // 不再在这里立即发送 PurchaseSuccess 事件，而是在验证成功后发送
                        // 避免过早触发远程状态刷新，导致状态闪烁
                    }
                } else {
                    LogUtils.w("Billing 购买成功但购买列表为空")
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.ShowError(
                                BillingErrorCode.PURCHASES_EMPTY,
                                isUserInitiated = true, // 购买流程是用户主动操作
                            )
                        )
                    }
                }
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                LogUtils.i("Billing 用户取消购买")
                // 发送用户取消事件，让 UI 层知道可以停止 loading
                eventScope.launch { eventFlow.emit(BillingEvent.UserCanceled) }
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                LogUtils.w("Billing Item already owned: User already has this subscription")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.ITEM_ALREADY_OWNED,
                            billingResult.responseCode,
                            "Item already owned",
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            "Item not owned",
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            "Item is not available in current region",
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            "Developer error",
                            isUserInitiated = true, // 购买流程是用户主动操作
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                LogUtils.e(
                    "Billing Service unavailable: Google Play services temporarily unavailable"
                )
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.SERVICE_UNAVAILABLE,
                            billingResult.responseCode,
                            "Service unavailable",
                            isUserInitiated = true, // 购买流程是用户主动操作
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                LogUtils.e(
                    "Billing Billing unavailable: Device does not support Google Play billing"
                )
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.BILLING_NOT_SUPPORTED,
                            billingResult.responseCode,
                            "Device does not support Google Play billing",
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            "Network error",
                            isUserInitiated = true, // 购买流程是用户主动操作
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                LogUtils.e(
                    "Billing Feature not supported: Current device does not support this feature"
                )
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.BILLING_FEATURE_NOT_SUPPORTED,
                            billingResult.responseCode,
                            "Feature not supported",
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            "General error",
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            billingResult.debugMessage,
                            isUserInitiated = true, // 购买流程是用户主动操作
                        )
                    )
                }
            }
        }
    }

    /** 处理购买 */
    private fun handlePurchase(purchase: Purchase) {
        if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
            // 乐观更新：立即更新UI状态，让用户立即看到状态变化
            // 然后在后台异步验证，如果验证失败再回滚
            val optimisticStatus =
                VipStatus(
                    isSubscribed = true,
                    subscriptionId = purchase.products.firstOrNull(),
                    purchaseTime = purchase.purchaseTime,
                )
            vipStatusFlow.value = optimisticStatus
            BillingStorage.saveLocalVipStatus(optimisticStatus)
            LogUtils.i("Billing ✅ 乐观更新订阅状态，UI将立即显示已订阅")

            // 后台异步执行确认和验证
            if (!purchase.isAcknowledged) {
                acknowledgePurchase(purchase)
            }

            // 调用后端验证订阅信息，如果验证失败则回滚状态
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
                // 确认成功，但不立即发送 PurchaseSuccess 事件
                // 等待后端验证成功后再发送，避免过早触发远程状态刷新
            } else {
                LogUtils.e("Billing 购买确认失败，回滚乐观更新状态: ${billingResult.debugMessage}")

                // 购买确认失败，回滚乐观更新
                rollbackOptimisticStatus()

                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            BillingErrorCode.PURCHASE_ACKNOWLEDGMENT_FAILED,
                            billingResult.responseCode,
                            billingResult.debugMessage,
                            isUserInitiated = true, // 购买流程是用户主动操作
                        )
                    )
                }
            }
        }
    }

    /** 调用后端验证订阅信息 */
    private fun verifySubscriptionWithServer(purchase: Purchase) {
        eventScope.launch {
            val purchaseProductsFirstId = purchase.products.firstOrNull() ?: ""
            try {
                // 重要：必须使用 purchase.products 中的 productId
                // 原因：
                // 1. purchase.products 和 purchase.purchaseToken 是配对的，必须使用 purchase.products 中的
                // productId
                // 2. 当有多个未确认的购买时（比如用户之前有月订阅，现在购买年订阅），
                //    onPurchasesUpdated 会返回所有未确认的购买
                // 3. Google Play 验证时，productId 和 purchaseToken 必须匹配，否则验证会失败
                // 构建验证请求
                val verifyRequest =
                    SubscriptionVerifyRequest(
                        productId = purchaseProductsFirstId, // 必须使用 purchase.products 中的 productId
                        purchaseToken = purchase.purchaseToken,
                        orderId = purchase.orderId ?: "",
                    )

                LogUtils.d(
                    "Billing 验证订阅: productId=${verifyRequest.productId}, purchaseToken=${verifyRequest.purchaseToken}, " +
                        "orderId=${verifyRequest.orderId}, purchaseTime=${purchase.purchaseTime}, " +
                        "purchaseState=${purchase.purchaseState}, isAcknowledged=${purchase.isAcknowledged}"
                )

                // 调用验证接口
                when (val result = api.verifySubscription(verifyRequest)) {
                    is HttpResult.Success -> {
                        val response = result.data
                        if (response.isVerified) {
                            LogUtils.i("Billing ✅ 订阅验证成功，状态已确认")
                            // 验证成功，更新完整状态信息（可能包含后端返回的额外信息）
                            val confirmedStatus =
                                VipStatus(
                                    isSubscribed = true,
                                    subscriptionId = purchase.products.firstOrNull(),
                                    purchaseTime = purchase.purchaseTime,
                                )
                            vipStatusFlow.value = confirmedStatus
                            BillingStorage.saveLocalVipStatus(confirmedStatus)

                            // 记录订阅验证成功事件
                            val productId = purchaseProductsFirstId
                            val plan =
                                plansFlow.value.firstOrNull { it.googleProductId == productId }
                            val eventParams =
                                mutableMapOf<String, Any>(
                                    "product_id" to productId,
                                    "order_id" to (purchase.orderId ?: ""),
                                    "purchase_token" to purchase.purchaseToken,
                                    "purchase_time" to purchase.purchaseTime,
                                    "user_type" to "vip",
                                    "timestamp" to System.currentTimeMillis(),
                                )
                            // 添加价格参数
                            plan?.let {
                                eventParams["price"] = it.price
                                eventParams["currency_code"] = it.currencyCode
                                eventParams["price_micros"] = it.priceAmountMicros
                            }
                            FirebaseManager.logEvent(
                                FirebaseManager.Events.SUBSCRIPTION_SUCCESS,
                                FirebaseManager.safeEventParams(
                                    *eventParams.map { it.key to it.value }.toTypedArray()
                                ),
                            )

                            // 验证成功后再发送 PurchaseSuccess 事件，触发远程状态刷新
                            // 此时后端已确认订阅，刷新不会导致状态回退
                            eventFlow.emit(BillingEvent.PurchaseSuccess(purchase))
                        } else {
                            LogUtils.w("Billing ⚠️ 订阅验证失败，回滚乐观更新状态: ${response.message}")
                            // 验证失败，回滚乐观更新
                            rollbackOptimisticStatus()

                            // 记录订阅验证失败事件
                            val productId = purchaseProductsFirstId
                            val plan =
                                plansFlow.value.firstOrNull { it.googleProductId == productId }
                            val eventParams =
                                mutableMapOf<String, Any>(
                                    "product_id" to productId,
                                    "order_id" to (purchase.orderId ?: ""),
                                    "purchase_token" to purchase.purchaseToken,
                                    "error_code" to (response.errorCode ?: ""),
                                    "error_message" to (response.message ?: ""),
                                    "purchase_time" to purchase.purchaseTime,
                                    "user_type" to
                                        if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    "timestamp" to System.currentTimeMillis(),
                                )
                            // 添加价格参数
                            plan?.let {
                                eventParams["price"] = it.price
                                eventParams["currency_code"] = it.currencyCode
                                eventParams["price_micros"] = it.priceAmountMicros
                            }
                            FirebaseManager.logEvent(
                                FirebaseManager.Events.SUBSCRIPTION_FAILURE,
                                FirebaseManager.safeEventParams(
                                    *eventParams.map { it.key to it.value }.toTypedArray()
                                ),
                            )

                            eventScope.launch {
                                eventFlow.emit(
                                    BillingEvent.ShowError(
                                        BillingErrorCode.SUBSCRIPTION_VERIFICATION_FAILED,
                                        response.message,
                                    )
                                )
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("Billing ❌ 订阅验证失败，回滚乐观更新状态: ${result.message}")
                        // 验证失败，回滚乐观更新
                        rollbackOptimisticStatus()

                        // 记录订阅验证失败事件
                        val productId = purchaseProductsFirstId
                        val plan = plansFlow.value.firstOrNull { it.googleProductId == productId }
                        val eventParams =
                            mutableMapOf<String, Any>(
                                "product_id" to productId,
                                "order_id" to (purchase.orderId ?: ""),
                                "purchase_token" to purchase.purchaseToken,
                                "error_message" to (result.message ?: ""),
                                "purchase_time" to purchase.purchaseTime,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "timestamp" to System.currentTimeMillis(),
                            )
                        // 添加价格参数
                        plan?.let {
                            eventParams["price"] = it.price
                            eventParams["currency_code"] = it.currencyCode
                            eventParams["price_micros"] = it.priceAmountMicros
                        }
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.SUBSCRIPTION_FAILURE,
                            FirebaseManager.safeEventParams(*eventParams.toList().toTypedArray()),
                        )

                        eventScope.launch {
                            eventFlow.emit(
                                BillingEvent.ShowError(
                                    BillingErrorCode.SUBSCRIPTION_VERIFICATION_FAILED,
                                    result.message,
                                )
                            )
                        }
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("Billing ❌ 订阅验证异常，回滚乐观更新状态: ${e.message}")
                // 验证异常，回滚乐观更新
                rollbackOptimisticStatus()

                // 记录订阅验证失败事件
                val productId = purchaseProductsFirstId
                val plan = plansFlow.value.firstOrNull { it.googleProductId == productId }
                val errorMessage = "${e.javaClass.simpleName}: ${e.message ?: ""}"
                val eventParams =
                    mutableMapOf<String, Any>(
                        "product_id" to productId,
                        "order_id" to (purchase.orderId ?: ""),
                        "purchase_token" to purchase.purchaseToken,
                        "error_message" to errorMessage,
                        "purchase_time" to purchase.purchaseTime,
                        "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                        "timestamp" to System.currentTimeMillis(),
                    )
                // 添加价格参数
                plan?.let {
                    eventParams["price"] = it.price
                    eventParams["currency_code"] = it.currencyCode
                    eventParams["price_micros"] = it.priceAmountMicros
                }
                FirebaseManager.logEvent(
                    FirebaseManager.Events.SUBSCRIPTION_FAILURE,
                    FirebaseManager.safeEventParams(*eventParams.toList().toTypedArray()),
                )

                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.ShowError(
                            BillingErrorCode.SUBSCRIPTION_VERIFICATION_EXCEPTION,
                            e.message,
                            isUserInitiated = true, // 购买流程是用户主动操作
                        )
                    )
                }
            }
        }
    }

    /** 回滚乐观更新的状态 */
    private fun rollbackOptimisticStatus() {
        val oldStatus = VipStatus(isSubscribed = false)
        vipStatusFlow.value = oldStatus
        BillingStorage.saveLocalVipStatus(oldStatus)
        LogUtils.w("Billing 已回滚乐观更新的订阅状态")
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
                            1001,
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_DISABLED,
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_MISSING,
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_INVALID,
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                            BillingErrorCode.GOOGLE_PLAY_SERVICE_UNAVAILABLE,
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                        BillingErrorCode.BILLING_NOT_SUPPORTED,
                        isUserInitiated = true, // 购买流程是用户主动操作
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
                            BillingErrorCode.BILLING_FEATURE_NOT_SUPPORTED,
                            isUserInitiated = true, // 购买流程是用户主动操作
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
                        e.message,
                        isUserInitiated = true, // 购买流程是用户主动操作
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
                        BillingErrorCode.PURCHASE_PRECONDITIONS_CHECK_FAILED,
                        isUserInitiated = true, // 购买流程是用户主动操作
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
        // 查询商品详情（使用 ProductDetails API - Billing Library 8.0+）
        val product =
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(productId)
                .setProductType(BillingClient.ProductType.SUBS)
                .build()

        val params = QueryProductDetailsParams.newBuilder().setProductList(listOf(product)).build()

        LogUtils.i("Billing [购买流程] 开始查询商品详情，商品ID: $productId")

        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsResult ->
            LogUtils.i(
                "Billing [购买流程] 查询商品详情结果: 响应码=${billingResult.responseCode}, 详情=${billingResult.debugMessage}"
            )

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    val productDetails = productDetailsResult?.productDetailsList?.firstOrNull()
                    productDetails?.let {
                        // 获取订阅优惠详情（通常使用第一个）
                        val subscriptionOfferDetails = it.subscriptionOfferDetails?.firstOrNull()
                        val offerToken = subscriptionOfferDetails?.offerToken

                        if (offerToken == null) {
                            LogUtils.e("Billing ❌ 未找到订阅优惠详情: $productId")
                            eventScope.launch {
                                eventFlow.emit(
                                    BillingEvent.SkuDetailsQueryFailed(
                                        BillingErrorCode.PRODUCT_DETAILS_NOT_FOUND,
                                        BillingClient.BillingResponseCode.OK,
                                        "No subscription offer details found for $productId",
                                        isUserInitiated = true, // 购买流程是用户主动操作
                                    )
                                )
                            }
                            return@queryProductDetailsAsync
                        }

                        val pricingPhase =
                            subscriptionOfferDetails.pricingPhases.pricingPhaseList.firstOrNull()
                        LogUtils.i(
                            "Billing [购买流程] ✅ 找到商品详情:\n" +
                                "  商品ID: ${it.productId}\n" +
                                "  标题: ${it.title}\n" +
                                "  描述: ${it.description}\n" +
                                "  原始价格: ${pricingPhase?.formattedPrice ?: "N/A"}\n" +
                                "  货币代码: ${pricingPhase?.priceCurrencyCode ?: "N/A"}\n" +
                                "  价格微单位: ${pricingPhase?.priceAmountMicros ?: 0L}\n" +
                                "  价格周期: ${pricingPhase?.billingPeriod ?: "N/A"}\n" +
                                "  优惠Token: $offerToken"
                        )

                        // 使用 ProductDetails 启动购买流程（Billing Library 8.0+）
                        val productDetailsParams =
                            BillingFlowParams.ProductDetailsParams.newBuilder()
                                .setProductDetails(it)
                                .setOfferToken(offerToken)
                                .build()

                        // 获取当前用户ID，用于设置 ObfuscatedAccountId
                        // 这样 webhook 可以通过 ObfuscatedAccountId 关联用户并创建订阅记录
                        val currentUserId = ai.sxwl.android.data.store.IntySetting.getCurUserID()

                        val billingFlowParamsBuilder =
                            BillingFlowParams.newBuilder()
                                .setProductDetailsParamsList(listOf(productDetailsParams))

                        // 设置 ObfuscatedAccountId（如果用户已登录）
                        // 这允许 webhook 通过 Google Play API 响应中的 obfuscatedExternalAccountId 字段关联用户
                        if (currentUserId.isNotEmpty()) {
                            billingFlowParamsBuilder.setObfuscatedAccountId(currentUserId)
                            LogUtils.d("Billing [购买流程] 设置 ObfuscatedAccountId: $currentUserId")
                        } else {
                            LogUtils.w("Billing [购买流程] 用户未登录，无法设置 ObfuscatedAccountId")
                        }

                        val billingFlowParams = billingFlowParamsBuilder.build()

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
                                        productId,
                                        isUserInitiated = true, // 购买流程是用户主动操作
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
                                "Please check product ID configuration, app signature, test user settings",
                                isUserInitiated = true, // 购买流程是用户主动操作
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
                                "Google Play services temporarily unavailable",
                                isUserInitiated = true, // 购买流程是用户主动操作
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
                                "Device does not support Google Play billing",
                                isUserInitiated = true, // 购买流程是用户主动操作
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
                                "Item is not available in current region",
                                isUserInitiated = true, // 购买流程是用户主动操作
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
                                "Network connection issue",
                                isUserInitiated = true, // 购买流程是用户主动操作
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
                                billingResult.debugMessage,
                                isUserInitiated = true, // 购买流程是用户主动操作
                            )
                        )
                    }
                }
            }
        }
    }
}
