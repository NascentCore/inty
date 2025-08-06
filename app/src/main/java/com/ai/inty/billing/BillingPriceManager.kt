package com.ai.inty.billing

import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.QueryProductDetailsParams
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/**
 * 计费价格管理类
 */
class BillingPriceManager(
    private val billingClient: BillingClient,
    private val eventScope: CoroutineScope,
    private val eventFlow: MutableSharedFlow<BillingEvent>,
    private val plansFlow: MutableStateFlow<List<VipPlan>>
) {

    /**
     * 查询商品详情并更新价格
     */
    fun querySkuDetails(isConnected: Boolean) {
        // 检查BillingClient连接状态
        if (!isConnected) {
            EasyLog.log("BillingRepository - BillingClient 未连接，无法查询商品")
            return
        }

        // 从 plansFlow 获取商品ID列表
        val currentPlans = plansFlow.value
        if (currentPlans.isEmpty()) {
            EasyLog.log("BillingRepository - plansFlow 为空，跳过价格查询")
            return
        }

        val subscriptionIds = currentPlans.map { it.googleProductId }
        EasyLog.log("BillingRepository - 从 plansFlow 获取商品ID: $subscriptionIds")

        // 使用新的 ProductDetails API
        val products = subscriptionIds.map { productId ->
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(productId)
                .setProductType(BillingClient.ProductType.SUBS)
                .build()
        }

        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(products)
            .build()

        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsResult ->
            EasyLog.log("BillingRepository - Google Play 价格查询结果: 响应码=${billingResult.responseCode}")
            EasyLog.log("BillingRepository - 查询结果详情: ${billingResult.debugMessage}")

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    productDetailsResult?.productDetailsList?.let { detailsList ->
                        if (detailsList.isNotEmpty()) {
                            EasyLog.log("BillingRepository - 查询成功，获取到 ${detailsList.size} 个商品信息")
                            // 使用新的 ProductDetails 更新计划价格
                            updateLocalPlans(currentPlans, detailsList)
                        } else {
                            EasyLog.log("BillingRepository - 查询成功但返回空商品列表，可能原因: 商品ID不存在或未在Google Play Console中激活")
                        }
                    } ?: run {
                        EasyLog.log("BillingRepository - Google Play返回的商品列表为null")
                    }
                }

                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    EasyLog.log("BillingRepository - 开发者错误 (12): 请检查商品ID配置、应用签名、测试用户设置")
                    EasyLog.log("BillingRepository - 当前查询的商品ID: $subscriptionIds")
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                billingResult.responseCode,
                                "开发者错误"
                            )
                        )
                    }
                }

                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    EasyLog.log("BillingRepository - 服务不可用: Google Play 服务暂时不可用")
                }

                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    EasyLog.log("BillingRepository - 计费不可用: 设备不支持 Google Play 计费")
                }

                BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                    EasyLog.log("BillingRepository - 商品未拥有: 用户未购买该商品")
                }

                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    EasyLog.log("BillingRepository - 商品不可用: 商品在当前地区不可用")
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    EasyLog.log("BillingRepository - 网络错误: 网络连接问题")
                }

                BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                    EasyLog.log("BillingRepository - 功能不支持: 当前设备不支持此功能")
                }

                BillingClient.BillingResponseCode.USER_CANCELED -> {
                    EasyLog.log("BillingRepository - 用户取消: 用户取消了操作")
                }

                BillingClient.BillingResponseCode.ERROR -> {
                    EasyLog.log("BillingRepository - 一般错误: 发生了未知错误")
                }

                else -> {
                    EasyLog.log("BillingRepository - 未知错误: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
                }
            }
        }
    }

    /**
     * 根据ProductDetails更新计划价格（新API方法）
     */
    private fun updateLocalPlans(
        currentPlans: List<VipPlan>,
        productDetailsList: List<ProductDetails>,
    ) {
        val updatedPlans = currentPlans.toMutableList()
        var updatedCount = 0

        EasyLog.log("开始比较价格信息 (新API)...")

        productDetailsList.forEach { productDetails ->
            val planId = productDetails.productId
            val index = updatedPlans.indexOfFirst { it.googleProductId == planId }

            if (index >= 0) {
                val currentPlan = updatedPlans[index]

                // 从 ProductDetails 中提取价格信息
                val offer = productDetails.subscriptionOfferDetails?.firstOrNull()
                val pricePhase = offer?.pricingPhases?.pricingPhaseList?.firstOrNull()

                if (pricePhase != null) {
                    val formattedPrice = pricePhase.formattedPrice
                    val currencyCode = pricePhase.priceCurrencyCode
                    val micros = pricePhase.priceAmountMicros
                    val correctedPrice =
                        BillingUtils.correctCurrencySymbol(formattedPrice, currencyCode)

                    // 检查价格是否有变化
                    if (currentPlan.price != correctedPrice ||
                        currentPlan.currencyCode != currencyCode ||
                        currentPlan.priceAmountMicros != micros
                    ) {

                        val oldPrice = currentPlan.price
                        updatedPlans[index] = currentPlan.copy(
                            price = correctedPrice,
                            originalPrice = correctedPrice,
                            currencyCode = currencyCode,
                            priceAmountMicros = micros
                        )
                        updatedCount++

                        EasyLog.log("✅ 价格有变化，更新计划: $planId")
                        EasyLog.log("   计划名称: ${currentPlan.name}")
                        EasyLog.log("   价格变化: $oldPrice -> $correctedPrice")
                        EasyLog.log("   货币代码: ${currentPlan.currencyCode} -> $currencyCode")
                        EasyLog.log("   商品标题: ${productDetails.title}")
                        EasyLog.log("   商品描述: ${productDetails.description}")
                    } else {
                        EasyLog.log("ℹ️ 价格无变化，跳过: $planId (${currentPlan.name})")
                    }
                } else {
                    EasyLog.log("⚠️ 未找到价格信息: $planId")
                }
            } else {
                EasyLog.log("⚠️ 未找到匹配的计划ID: $planId")
            }
        }

        // 如果有变化，更新并通知
        if (updatedCount > 0) {
            EasyLog.log("✅ 检测到 $updatedCount 个计划价格变化，更新 plansFlow")
            plansFlow.value = updatedPlans
            BillingStorage.saveLocalPlans(updatedPlans) // 保存到本地缓存
        } else {
            EasyLog.log("ℹ️ 所有计划价格都无变化，无需更新")
        }
    }
} 
