package com.ai.inty.billing

import ai.sxwl.android.utils.LogUtils
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.SkuDetails
import com.android.billingclient.api.SkuDetailsParams
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/* 从 Google Play 查询实时价格：
 * 使用已弃用但仍可用的 SkuDetails API
 * 查询订阅商品的价格信息
 * 更新本地 VipPlan 对象，包含：
 * - 格式化的价格字符串
 * -货币代码
 * -微单位价格
 * 处理货币符号修正
 * 仅在 BillingClient 连接时查询价格
 */
internal class BillingPriceManager(
    private val billingClient: BillingClient,
    private val eventScope: CoroutineScope,
    private val eventFlow: MutableSharedFlow<BillingEvent>,
    private val plansFlow: MutableStateFlow<List<VipPlan>>,
) {

    /** 查询商品详情并更新价格 */
    fun querySkuDetails(isConnected: Boolean) {
        // 检查BillingClient连接状态
        if (!isConnected) {
            LogUtils.w("BillingClient 未连接，无法查询商品")
            return
        }

        // 从 plansFlow 获取商品ID列表
        val currentPlans = plansFlow.value
        if (currentPlans.isEmpty()) {
            LogUtils.w("plansFlow 为空，跳过价格查询")
            return
        }

        val subscriptionIds = currentPlans.map { it.googleProductId }
        LogUtils.d("从 plansFlow 获取商品ID: $subscriptionIds")

        // 使用 SkuDetails API
        val params =
            SkuDetailsParams.newBuilder()
                .setSkusList(subscriptionIds)
                .setType(BillingClient.SkuType.SUBS)
                .build()

        billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
            LogUtils.d("Google Play 价格查询结果: 响应码=${billingResult.responseCode}, 详情: ${billingResult.debugMessage}")

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    skuDetailsList?.let { detailsList ->
                        if (detailsList.isNotEmpty()) {
                            LogUtils.i("查询成功，获取到 ${detailsList.size} 个商品信息")
                            // 使用 SkuDetails 更新计划价格
                            updateLocalPlans(currentPlans, detailsList)
                        } else {
                            LogUtils.w("查询成功但返回空商品列表，可能原因: 商品ID不存在或未在Google Play Console中激活")
                            // 发送查询失败事件
                            eventScope.launch {
                                eventFlow.emit(
                                    BillingEvent.SkuDetailsQueryFailed(
                                        billingResult.responseCode,
                                        "查询成功但返回空商品列表",
                                    )
                                )
                            }
                        }
                    } ?: run {
                        LogUtils.w("Google Play返回的商品列表为null")
                        eventScope.launch {
                            eventFlow.emit(
                                BillingEvent.SkuDetailsQueryFailed(
                                    billingResult.responseCode,
                                    "Google Play返回的商品列表为null",
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
                                billingResult.debugMessage,
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
                                billingResult.debugMessage,
                            )
                        )
                    }
                }
            }
        }
    }

    /** 根据SkuDetails更新计划价格（旧API方法） */
    private fun updateLocalPlans(currentPlans: List<VipPlan>, skuDetailsList: List<SkuDetails>) {
        val updatedPlans = currentPlans.toMutableList()
        var updatedCount = 0

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
                if (
                    currentPlan.price != correctedPrice ||
                    currentPlan.currencyCode != currencyCode ||
                    currentPlan.priceAmountMicros != micros
                ) {

                    val oldPrice = currentPlan.price
                    updatedPlans[index] =
                        currentPlan.copy(
                            price = correctedPrice,
                            originalPrice = correctedPrice,
                            currencyCode = currencyCode,
                            priceAmountMicros = micros,
                        )
                    updatedCount++

                    LogUtils.i("✅ 价格有变化，更新计划: $planId, 名称: ${currentPlan.name}, 价格: $oldPrice -> $correctedPrice, 货币: ${currentPlan.currencyCode} -> $currencyCode")
                } else {
                    LogUtils.d("ℹ️ 价格无变化，跳过: $planId (${currentPlan.name})")
                }
            } else {
                LogUtils.w("⚠️ 未找到匹配的计划ID: $planId")
            }
        }

        // 如果有变化，更新并通知
        if (updatedCount > 0) {
            LogUtils.i("✅ 检测到 $updatedCount 个计划价格变化，更新 plansFlow")
            plansFlow.value = updatedPlans
            BillingStorage.saveLocalPlans(updatedPlans) // 保存到本地缓存
        } else {
            LogUtils.d("ℹ️ 所有计划价格都无变化，无需更新")
        }
    }
}
