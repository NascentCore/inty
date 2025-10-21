package com.ai.inty.billing

import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.SkuDetails
import com.android.billingclient.api.SkuDetailsParams
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/** 计费价格管理类 */
internal class BillingPriceManager(
    private val billingClient: BillingClient,
    private val eventScope: CoroutineScope,
    private val eventFlow: MutableSharedFlow<BillingEvent>,
    private val plansFlow: MutableStateFlow<List<VipPlan>>,
) {

    /** 查询商品详情并更新价格 */
    fun querySkuDetails() {
        // 从 plansFlow 获取商品ID列表
        val currentPlans = plansFlow.value
        if (currentPlans.isEmpty()) {
            EasyLog.log("BillingRepository BillingPriceManager - plansFlow 为空，跳过价格查询")
            return
        }

        val subscriptionIds = currentPlans.map { it.googleProductId }
        EasyLog.log("BillingRepository BillingPriceManager - 从 plansFlow 获取商品ID: $subscriptionIds")

        // 使用 SkuDetails API
        val params =
            SkuDetailsParams.newBuilder()
                .setSkusList(subscriptionIds)
                .setType(BillingClient.SkuType.SUBS)
                .build()

        billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
            EasyLog.log(
                "BillingRepository BillingPriceManager - Google Play 价格查询结果: 响应码=${billingResult.responseCode}"
            )
            EasyLog.log(
                "BillingRepository BillingPriceManager - 查询结果详情: ${billingResult.debugMessage}"
            )

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    skuDetailsList?.let { detailsList ->
                        if (detailsList.isNotEmpty()) {
                            EasyLog.log(
                                "BillingRepository BillingPriceManager - 查询成功，获取到 ${detailsList.size} 个商品信息，\n${
                                    detailsList.joinToString(
                                        " ,, "
                                    )
                                }"
                            )
                            // 使用 SkuDetails 更新计划价格
                            updateLocalPlans(currentPlans, detailsList)
                        } else {
                            EasyLog.log(
                                "BillingRepository BillingPriceManager - 查询成功但返回空商品列表，可能原因: 商品ID不存在或未在Google Play Console中激活"
                            )
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
                    }
                        ?: run {
                            EasyLog.log(
                                "BillingRepository BillingPriceManager - Google Play返回的商品列表为null"
                            )
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
// 即使查询失败，也使用静态价格显示
EasyLog.log("BillingRepository BillingPriceManager - 价格查询失败，使用静态价格显示")

updatePlansWithStaticPrices()

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
                    
// 即使查询失败，也使用静态价格显示
EasyLog.log("BillingRepository BillingPriceManager - 未知错误，使用静态价格显示")

updatePlansWithStaticPrices()

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

/** 使用静态价格更新计划（当 billing 不可用时） */
private fun updatePlansWithStaticPrices() {
    val currentPlans = plansFlow.value
    if (currentPlans.isEmpty()) {
        EasyLog.log("BillingRepository BillingPriceManager - plansFlow 为空，无法设置静态价格")
        return
    }

    val updatedPlans =
            currentPlans.map { plan ->
                // 如果价格还是占位符 "-"，则设置静态价格
                if (plan.price == "-" || plan.price.isEmpty()) {
                    val staticPrice = getStaticPriceForPlan(plan)
                    EasyLog.log(
                            "BillingRepository BillingPriceManager - 设置静态价格: ${plan.name} -> $staticPrice"
                    )
                    plan.copy(
                            price = staticPrice,
                            originalPrice = staticPrice,
                            currencyCode = "USD", // 默认货币
                            priceAmountMicros = 0L // 静态价格不设置微秒值
                    )
                } else {
                    plan // 保持现有价格
                }
            }

    // 更新 plansFlow
    plansFlow.value = updatedPlans
    BillingStorage.saveLocalPlans(updatedPlans)
    EasyLog.log("BillingRepository BillingPriceManager - 静态价格更新完成")
}

/** 根据计划类型获取静态价格 */
private fun getStaticPriceForPlan(plan: VipPlan): String {
    return when {
        plan.name.contains("monthly", ignoreCase = true) ||
                plan.name.contains("月", ignoreCase = true) -> "$9.99/月"
        plan.name.contains("yearly", ignoreCase = true) ||
                plan.name.contains("年", ignoreCase = true) -> "$99.99/年"
        plan.name.contains("weekly", ignoreCase = true) ||
                plan.name.contains("周", ignoreCase = true) -> "$2.99/周"
        plan.name.contains("premium", ignoreCase = true) -> "$9.99/月"
        plan.name.contains("pro", ignoreCase = true) -> "$19.99/月"
        plan.name.contains("basic", ignoreCase = true) -> "$4.99/月"
        else -> "$9.99/月" // 默认价格
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

                    EasyLog.log("BillingRepository BillingPriceManager ✅ 价格有变化，更新计划: $planId")
                    EasyLog.log(
                        "BillingRepository BillingPriceManager    计划名称: ${currentPlan.name}"
                    )
                    EasyLog.log(
                        "BillingRepository BillingPriceManager    价格变化: $oldPrice -> $correctedPrice"
                    )
                    EasyLog.log(
                        "BillingRepository BillingPriceManager    货币代码: ${currentPlan.currencyCode} -> $currencyCode"
                    )
                    EasyLog.log(
                        "BillingRepository BillingPriceManager    商品标题: ${skuDetails.title}"
                    )
                    EasyLog.log(
                        "BillingRepository BillingPriceManager    商品描述: ${skuDetails.description}"
                    )
                } else {
                    EasyLog.log(
                        "BillingRepository BillingPriceManager ℹ️ 价格无变化，跳过: $planId (${currentPlan.name})"
                    )
                }
            } else {
                EasyLog.log("BillingRepository BillingPriceManager ⚠️ 未找到匹配的计划ID: $planId")
            }
        }

        // 如果有变化，更新并通知
        if (updatedCount > 0) {
            EasyLog.log(
                "BillingRepository BillingPriceManager ✅ 检测到 $updatedCount 个计划价格变化，更新 plansFlow"
            )
            plansFlow.value = updatedPlans
            BillingStorage.saveLocalPlans(updatedPlans) // 保存到本地缓存
        } else {
            EasyLog.log("BillingRepository BillingPriceManager ℹ️ 所有计划价格都无变化，无需更新")
        }
    }
}
