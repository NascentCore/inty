package com.ai.inty.billing

import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.SkuDetails
import com.android.billingclient.api.SkuDetailsParams
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/**
 * 计费价格管理类
 */
internal class BillingPriceManager(
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
            EasyLog.log("BillingRepository BillingPriceManager - BillingClient 未连接，无法查询商品")
            return
        }

        // 从 plansFlow 获取商品ID列表
        val currentPlans = plansFlow.value
        if (currentPlans.isEmpty()) {
            EasyLog.log("BillingRepository BillingPriceManager - plansFlow 为空，跳过价格查询")
            return
        }

        val subscriptionIds = currentPlans.map { it.googleProductId }
        EasyLog.log("BillingRepository BillingPriceManager - 从 plansFlow 获取商品ID: $subscriptionIds")

        // 使用 SkuDetails API
        val params = SkuDetailsParams.newBuilder()
            .setSkusList(subscriptionIds)
            .setType(BillingClient.SkuType.SUBS)
            .build()

        billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
            EasyLog.log("BillingRepository BillingPriceManager - Google Play 价格查询结果: 响应码=${billingResult.responseCode}", EasyLog.DEBUG)
            EasyLog.log("BillingRepository BillingPriceManager - 查询结果详情: ${billingResult.debugMessage}", EasyLog.DEBUG)

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    skuDetailsList?.let { detailsList ->
                        if (detailsList.isNotEmpty()) {
                            EasyLog.log("BillingRepository BillingPriceManager - 查询成功，获取到 ${detailsList.size} 个商品信息", EasyLog.DEBUG)
                            EasyLog.log(
                                "BillingRepository BillingPriceManager - 查询成功，获取到 ${
                                    detailsList.joinToString(
                                        " ,, "
                                    )
                                } 个商品信息", EasyLog.DEBUG
                            )
                            // 使用 SkuDetails 更新计划价格
                            updateLocalPlans(currentPlans, detailsList)
                        } else {
                            EasyLog.log("BillingRepository BillingPriceManager - 查询成功但返回空商品列表，可能原因: 商品ID不存在或未在Google Play Console中激活")
                            // 发送查询失败事件
                            eventScope.launch {
                                eventFlow.emit(
                                    BillingEvent.SkuDetailsQueryFailed(
                                        billingResult.responseCode,
                                        "查询成功但返回空商品列表"
                                    )
                                )
                            }
                        }
                    } ?: run {
                        EasyLog.log("BillingRepository BillingPriceManager - Google Play返回的商品列表为null")
                        eventScope.launch {
                            eventFlow.emit(
                                BillingEvent.SkuDetailsQueryFailed(
                                    billingResult.responseCode,
                                    "Google Play返回的商品列表为null"
                                )
                            )
                        }
                    }
                }

                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE,
                BillingClient.BillingResponseCode.DEVELOPER_ERROR,
                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE,
                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    // 使用统一的错误处理
                    BillingErrorHandler.handlePriceQueryError(billingResult)
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                billingResult.responseCode,
                                billingResult.debugMessage
                            )
                        )
                    }
                }
                else -> {
                    // 使用统一的错误处理
                    BillingErrorHandler.handlePriceQueryError(billingResult)

                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                billingResult.responseCode,
                                billingResult.debugMessage
                            )
                        )
                    }
                }
            }
        }
    }

    /**
     * 根据SkuDetails更新计划价格（旧API方法）
     */
    private fun updateLocalPlans(
        currentPlans: List<VipPlan>,
        skuDetailsList: List<SkuDetails>,
    ) {
        val updatedPlans = currentPlans.toMutableList()
        var updatedCount = 0

        EasyLog.log("BillingRepository BillingPriceManager 开始比较价格信息 (旧API)...", EasyLog.DEBUG)

        skuDetailsList.forEach { skuDetails ->
            val planId = skuDetails.sku
            val index = updatedPlans.indexOfFirst { it.googleProductId == planId }

            if (index >= 0) {
                val currentPlan = updatedPlans[index]

                // 从 SkuDetails 中提取价格信息
                val formattedPrice = skuDetails.price
                val currencyCode = skuDetails.priceCurrencyCode
                val micros = skuDetails.priceAmountMicros
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

                    EasyLog.log("BillingRepository BillingPriceManager ✅ 价格有变化，更新计划: $planId", EasyLog.DEBUG)
                    EasyLog.log("BillingRepository BillingPriceManager    计划名称: ${currentPlan.name}", EasyLog.DEBUG)
                    EasyLog.log("BillingRepository BillingPriceManager    价格变化: $oldPrice -> $correctedPrice", EasyLog.DEBUG)
                    EasyLog.log("BillingRepository BillingPriceManager    货币代码: ${currentPlan.currencyCode} -> $currencyCode", EasyLog.DEBUG)
                    EasyLog.log("BillingRepository BillingPriceManager    商品标题: ${skuDetails.title}", EasyLog.DEBUG)
                    EasyLog.log("BillingRepository BillingPriceManager    商品描述: ${skuDetails.description}", EasyLog.DEBUG)
                } else {
                    EasyLog.log("BillingRepository BillingPriceManager ℹ️ 价格无变化，跳过: $planId (${currentPlan.name})", EasyLog.DEBUG)
                }
            } else {
                EasyLog.log("BillingRepository BillingPriceManager ⚠️ 未找到匹配的计划ID: $planId", EasyLog.DEBUG)
            }
        }

        // 如果有变化，更新并通知
        if (updatedCount > 0) {
            EasyLog.log("BillingRepository BillingPriceManager ✅ 检测到 $updatedCount 个计划价格变化，更新 plansFlow", EasyLog.DEBUG)
            plansFlow.value = updatedPlans
            BillingStorage.saveLocalPlans(updatedPlans) // 保存到本地缓存
        } else {
            EasyLog.log("BillingRepository BillingPriceManager ℹ️ 所有计划价格都无变化，无需更新", EasyLog.DEBUG)
        }
    }
} 
