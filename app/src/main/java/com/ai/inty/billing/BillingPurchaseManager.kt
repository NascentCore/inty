package com.ai.inty.billing

import android.app.Activity
import com.ai.inty.beans.SubscriptionVerifyRequest
import com.ai.inty.net.ISubscriptionApi
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.QueryProductDetailsParams
import com.architecture.httplib.core.HttpResult
import com.google.android.gms.common.GoogleApiAvailability
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/**
 * 计费购买管理类
 */
class BillingPurchaseManager(
    private val billingClient: BillingClient,
    private val eventScope: CoroutineScope,
    private val eventFlow: MutableSharedFlow<BillingEvent>,
    private val vipStatusFlow: MutableStateFlow<VipStatus>
) {

    private val api = TheRouter.get(ISubscriptionApi::class.java)
        ?: error("Billing Purchase Manager theRouter init Error")

    /**
     * 处理购买更新
     */
    fun onPurchasesUpdated(billingResult: BillingResult, purchases: MutableList<Purchase>?) {
        EasyLog.log("BillingRepository - 购买更新回调: 响应码=${billingResult.responseCode}")

        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                if (purchases != null && purchases.isNotEmpty()) {
                    EasyLog.log("BillingRepository - 购买成功，处理 ${purchases.size} 个购买")
                    for (purchase in purchases) {
                        handlePurchase(purchase)
                        // 发送购买成功事件
                        eventScope.launch {
                            eventFlow.emit(BillingEvent.PurchaseSuccess(purchase))
                        }
                    }
                } else {
                    EasyLog.log("BillingRepository - 购买成功但购买列表为空")
                }
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                EasyLog.log("BillingRepository - 用户取消购买")
                // 用户取消不发送失败事件
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                EasyLog.log("BillingRepository - 商品已拥有: 用户已经拥有该订阅")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "商品已拥有"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                EasyLog.log("BillingRepository - 商品未拥有: 用户未购买该商品")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "商品未拥有"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                EasyLog.log("BillingRepository - 商品不可用: 商品在当前地区不可用")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "商品在当前地区不可用"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                EasyLog.log("BillingRepository - 开发者错误: 请检查商品ID配置、应用签名、测试用户设置")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "开发者错误"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                EasyLog.log("BillingRepository - 服务不可用: Google Play 服务暂时不可用")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "服务不可用"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                EasyLog.log("BillingRepository - 计费不可用: 设备不支持 Google Play 计费")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "设备不支持 Google Play 计费"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                EasyLog.log("BillingRepository - 网络错误: 网络连接问题")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "网络错误"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                EasyLog.log("BillingRepository - 功能不支持: 当前设备不支持此功能")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "功能不支持"
                        )
                    )
                }
            }

            BillingClient.BillingResponseCode.ERROR -> {
                EasyLog.log("BillingRepository - 一般错误: 发生了未知错误")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            "一般错误"
                        )
                    )
                }
            }

            else -> {
                EasyLog.log("BillingRepository - 购买失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
                eventScope.launch {
                    eventFlow.emit(
                        BillingEvent.PurchaseFailed(
                            billingResult.responseCode,
                            billingResult.debugMessage
                        )
                    )
                }
            }
        }
    }

    /**
     * 处理购买
     */
    private fun handlePurchase(purchase: Purchase) {
        if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
            if (!purchase.isAcknowledged) {
                acknowledgePurchase(purchase)
            }

            // 调用后端验证订阅信息
            verifySubscriptionWithServer(purchase)

            // 更新会员状态为已订阅
            val newStatus = VipStatus(
                isSubscribed = true,
                subscriptionId = purchase.products.firstOrNull(),
                purchaseTime = purchase.purchaseTime,
                expiryTime = 0L // 需要从服务器获取过期时间
            )
            vipStatusFlow.value = newStatus
            BillingStorage.saveLocalVipStatus(newStatus)
        }
    }

    /**
     * 确认购买
     */
    private fun acknowledgePurchase(purchase: Purchase) {
        val acknowledgePurchaseParams = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        billingClient.acknowledgePurchase(acknowledgePurchaseParams) { billingResult ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                EasyLog.log("BillingRepository - 购买确认成功")
            }
        }
    }

    /**
     * 调用后端验证订阅信息
     */
    private fun verifySubscriptionWithServer(purchase: Purchase) {
        eventScope.launch {
            try {
                // 构建验证请求
                val verifyRequest = SubscriptionVerifyRequest(
                    productId = purchase.products.firstOrNull() ?: "",
                    purchaseToken = purchase.purchaseToken,
                    orderId = purchase.orderId ?: ""
                )

                EasyLog.log("验证订阅: productId=${verifyRequest.productId}, purchaseToken=${verifyRequest.purchaseToken}, orderId=${verifyRequest.orderId}")

                // 调用验证接口
                val result = api.verifySubscription(verifyRequest)

                when (result) {
                    is HttpResult.Success -> {
                        val response = result.data
                        if (response.isValid) {
                            EasyLog.log("✅ 订阅验证成功")
                        } else {
                            EasyLog.log("⚠️ 订阅验证失败: ${response.message}")
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log("❌ 订阅验证失败: ${result.message}")
                    }
                }

            } catch (e: Exception) {
                EasyLog.log("❌ 订阅验证异常: ${e.message}")
            }
        }
    }

    /**
     * 检查购买前的状态
     */
    fun checkPurchasePreconditions(activity: Activity): Boolean {
        // 检查 Google Play 服务是否可用
        val googleApiAvailability = GoogleApiAvailability.getInstance()
        val context = activity.applicationContext
        val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)

        EasyLog.log("Google Play 服务检查结果: $resultCode")

        when (resultCode) {
            com.google.android.gms.common.ConnectionResult.SUCCESS -> {
                EasyLog.log("✅ Google Play 服务可用")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> {
                EasyLog.log("⚠️ Google Play 服务需要更新")
                // 尝试更新 Google Play 服务
                googleApiAvailability.getErrorDialog(activity, resultCode, 1001)?.show()
                return false
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_DISABLED -> {
                EasyLog.log("❌ Google Play 服务被禁用")
                return false
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_MISSING -> {
                EasyLog.log("❌ Google Play 服务未安装")
                return false
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_INVALID -> {
                EasyLog.log("❌ Google Play 服务无效")
                return false
            }

            else -> {
                EasyLog.log("❌ Google Play 服务不可用: $resultCode")
                return false
            }
        }

        // 检查设备是否支持计费
        if (!isBillingSupported()) {
            EasyLog.log("❌ 设备不支持 Google Play 计费")
            return false
        }

        return true
    }

    /**
     * 检查设备是否支持计费
     */
    private fun isBillingSupported(): Boolean {
        return try {
            val billingResult =
                billingClient.isFeatureSupported(BillingClient.FeatureType.SUBSCRIPTIONS)
            val isSupported = billingResult.responseCode == BillingClient.BillingResponseCode.OK
            EasyLog.log("设备计费支持检查: $isSupported (响应码: ${billingResult.responseCode})")
            EasyLog.log("计费支持检查详情: ${billingResult.debugMessage}")
            isSupported
        } catch (e: Exception) {
            EasyLog.log("检查计费支持时出错: ${e.message}")
            EasyLog.log("异常堆栈: ${e.stackTraceToString()}")
            false
        }
    }

    /**
     * 启动购买流程
     */
    fun launchBillingFlow(activity: Activity, productId: String) {
        // 检查购买前条件
        if (!checkPurchasePreconditions(activity)) return

        EasyLog.log("开始启动购买流程，商品ID: $productId")

        // 执行购买流程
        launchBillingFlowInternal(activity, productId)
    }

    /**
     * 内部购买流程实现
     */
    private fun launchBillingFlowInternal(activity: Activity, productId: String) {
        // 先查询商品详情（使用新的 ProductDetails API）
        val product = QueryProductDetailsParams.Product.newBuilder()
            .setProductId(productId)
            .setProductType(BillingClient.ProductType.SUBS)
            .build()

        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(listOf(product))
            .build()

        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsResult ->
            EasyLog.log("BillingRepository - 查询商品详情结果: 响应码=${billingResult.responseCode}")

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    productDetailsResult.productDetailsList.firstOrNull()?.let { productDetails ->
                        EasyLog.log("✅ 找到商品详情: ${productDetails.productId}")
                        EasyLog.log("   商品标题: ${productDetails.title}")
                        EasyLog.log("   商品描述: ${productDetails.description}")

                        // 获取价格信息
                        val offer = productDetails.subscriptionOfferDetails?.firstOrNull()
                        val pricePhase = offer?.pricingPhases?.pricingPhaseList?.firstOrNull()
                        if (pricePhase != null) {
                            EasyLog.log("   价格: ${pricePhase.formattedPrice}")
                            EasyLog.log("   货币代码: ${pricePhase.priceCurrencyCode}")
                        }

                        // 对于订阅产品，需要提供 offerToken 启动购买流程（使用新的 ProductDetails）
                        if (offer != null) {
                            val billingFlowParams = BillingFlowParams.newBuilder()
                                .setProductDetailsParamsList(
                                    listOf(
                                        BillingFlowParams.ProductDetailsParams.newBuilder()
                                            .setProductDetails(productDetails)
                                            .setOfferToken(offer.offerToken)  // 添加 offerToken
                                            .build()
                                    )
                                )
                                .build()
                            val launchResult =
                                billingClient.launchBillingFlow(activity, billingFlowParams)
                            EasyLog.log("✅ 购买流程启动结果: $launchResult")
                        }

                    } ?: run {
                        EasyLog.log("❌ 未找到商品详情: $productId")
                        EasyLog.log("可能原因:")
                        EasyLog.log("  1. 商品ID不存在于Google Play Console")
                        EasyLog.log("  2. 商品未激活或未发布")
                        EasyLog.log("  3. 应用签名与Google Play Console不匹配")
                        EasyLog.log("  4. 测试用户未正确设置")
                    }
                }

                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    EasyLog.log("❌ 开发者错误 (12): 请检查商品ID配置、应用签名、测试用户设置")
                    EasyLog.log("当前查询的商品ID: $productId")
                }

                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    EasyLog.log("❌ 服务不可用: Google Play 服务暂时不可用")
                }

                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    EasyLog.log("❌ 计费不可用: 设备不支持 Google Play 计费")
                }

                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    EasyLog.log("❌ 商品不可用: 商品在当前地区不可用")
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    EasyLog.log("❌ 网络错误: 网络连接问题")
                }

                else -> {
                    EasyLog.log("❌ 查询商品详情失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
                }
            }
        }
    }
} 
