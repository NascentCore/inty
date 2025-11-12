package ai.sxwl.android.data.billing

import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.QueryProductDetailsParams
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/* 从 Google Play 查询实时价格：
 * 使用 ProductDetails API (Billing Library 8.0+)
 * 查询订阅商品的价格信息
 * 更新本地 VipPlan 对象，包含：
 * - 格式化的价格字符串
 * - 货币代码
 * - 微单位价格
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
    fun queryProductDetails(isConnected: Boolean) {
        // 检查BillingClient连接状态
        if (!isConnected) {
            LogUtils.w("Billing Billing [价格查询] BillingClient 未连接，无法查询商品")
            return
        }

        // 从 plansFlow 获取商品ID列表（在异步回调外获取，避免竞态）
        val currentPlansBeforeQuery = plansFlow.value
        val subscriptionIds = currentPlansBeforeQuery.map { it.googleProductId }
        if (subscriptionIds.isEmpty()) {
            LogUtils.w("Billing [价格查询] plansFlow 为空，跳过价格查询")
            return
        }

        LogUtils.i("Billing [价格查询] 开始查询价格，商品ID列表: $subscriptionIds")
        LogUtils.d("Billing [价格查询] 当前计划状态:")
        currentPlansBeforeQuery.forEach { plan ->
            LogUtils.d(
                "  - ${plan.googleProductId}: ${plan.name}, 当前价格=${plan.price}, 货币=${plan.currencyCode}, 微单位=${plan.priceAmountMicros}"
            )
        }

        // 使用 ProductDetails API (Billing Library 8.0+)
        val productList =
            subscriptionIds.map { productId ->
                QueryProductDetailsParams.Product.newBuilder()
                    .setProductId(productId)
                    .setProductType(BillingClient.ProductType.SUBS)
                    .build()
            }

        val params = QueryProductDetailsParams.newBuilder().setProductList(productList).build()

        LogUtils.d("Billing [价格查询] 调用 queryProductDetailsAsync，查询 ${subscriptionIds.size} 个商品")

        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsResult ->
            LogUtils.i(
                "Billing [价格查询] Google Play 返回结果: 响应码=${billingResult.responseCode}, 详情=${billingResult.debugMessage}"
            )

            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    val detailsList = productDetailsResult?.productDetailsList
                    if (detailsList != null && detailsList.isNotEmpty()) {
                        LogUtils.i("Billing [价格查询] ✅ 查询成功，获取到 ${detailsList.size} 个商品信息")

                        // 详细记录每个商品的价格信息
                        LogUtils.i("Billing [价格查询] Google Play 返回的商品详情:")
                        detailsList.forEach { productDetails ->
                            val subscriptionOfferDetails =
                                productDetails.subscriptionOfferDetails?.firstOrNull()
                            val pricingPhase =
                                subscriptionOfferDetails
                                    ?.pricingPhases
                                    ?.pricingPhaseList
                                    ?.firstOrNull()
                            LogUtils.i(
                                "  📦 商品ID: ${productDetails.productId}\n" +
                                    "     标题: ${productDetails.title}\n" +
                                    "     描述: ${productDetails.description}\n" +
                                    "     原始价格: ${pricingPhase?.formattedPrice ?: "N/A"}\n" +
                                    "     货币代码: ${pricingPhase?.priceCurrencyCode ?: "N/A"}\n" +
                                    "     价格微单位: ${pricingPhase?.priceAmountMicros ?: 0L}\n" +
                                    "     价格周期: ${pricingPhase?.billingPeriod ?: "N/A"}"
                            )
                        }

                        // 在异步回调中重新获取最新的plansFlow，避免使用旧值
                        val latestPlans = plansFlow.value
                        LogUtils.d("Billing [价格查询] 开始更新本地计划价格，当前本地计划数量: ${latestPlans.size}")
                        // 使用 ProductDetails 更新计划价格
                        updateLocalPlans(latestPlans, detailsList)
                    } else if (detailsList != null && detailsList.isEmpty()) {
                        LogUtils.w("Billing [价格查询] ⚠️ 查询成功但返回空商品列表")
                        LogUtils.w("Billing [价格查询] 可能原因: 商品ID不存在或未在Google Play Console中激活")
                        LogUtils.w("Billing [价格查询] 查询的商品ID: $subscriptionIds")
                        // 发送查询失败事件
                        eventScope.launch {
                            eventFlow.emit(
                                BillingEvent.SkuDetailsQueryFailed(
                                    BillingErrorCode.PRODUCT_DETAILS_QUERY_FAILED,
                                    billingResult.responseCode,
                                    "查询成功但返回空商品列表",
                                )
                            )
                        }
                    } else {
                        LogUtils.w("Billing [价格查询] ⚠️ Google Play返回的商品列表为null")
                        LogUtils.w("Billing [价格查询] 查询的商品ID: $subscriptionIds")
                        eventScope.launch {
                            eventFlow.emit(
                                BillingEvent.SkuDetailsQueryFailed(
                                    BillingErrorCode.PRODUCT_DETAILS_QUERY_FAILED,
                                    billingResult.responseCode,
                                    "Google Play返回的商品列表为null",
                                )
                            )
                        }
                    }
                }

                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    // 记录错误日志
                    BillingErrorLogger.handlePriceQueryError(billingResult)
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.BILLING_NOT_SUPPORTED,
                                billingResult.responseCode,
                                billingResult.debugMessage,
                            )
                        )
                    }
                }

                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    // 使用统一的错误处理
                    BillingErrorLogger.handlePriceQueryError(billingResult)
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.DEVELOPER_ERROR,
                                billingResult.responseCode,
                                billingResult.debugMessage,
                            )
                        )
                    }
                }

                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    // 使用统一的错误处理
                    BillingErrorLogger.handlePriceQueryError(billingResult)
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.SERVICE_UNAVAILABLE,
                                billingResult.responseCode,
                                billingResult.debugMessage,
                            )
                        )
                    }
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    // 使用统一的错误处理
                    BillingErrorLogger.handlePriceQueryError(billingResult)
                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.NETWORK_ERROR,
                                billingResult.responseCode,
                                billingResult.debugMessage,
                            )
                        )
                    }
                }

                else -> {
                    // 使用统一的错误处理
                    BillingErrorLogger.handlePriceQueryError(billingResult)

                    eventScope.launch {
                        eventFlow.emit(
                            BillingEvent.SkuDetailsQueryFailed(
                                BillingErrorCode.UNKNOWN_ERROR,
                                billingResult.responseCode,
                                billingResult.debugMessage,
                            )
                        )
                    }
                }
            }
        }
    }

    /** 根据ProductDetails更新计划价格（Billing Library 8.0+ API） */
    private fun updateLocalPlans(
        currentPlans: List<VipPlan>,
        productDetailsList: List<ProductDetails>,
    ) {
        LogUtils.i("Billing [价格更新] 开始处理 ${productDetailsList.size} 个商品的价格更新")

        val updatedPlans = currentPlans.toMutableList()
        var updatedCount = 0

        productDetailsList.forEach { productDetails ->
            val planId = productDetails.productId
            val index = updatedPlans.indexOfFirst { it.googleProductId == planId }

            if (index >= 0) {
                val currentPlan = updatedPlans[index]

                // 从 ProductDetails 中提取价格信息（订阅商品）
                val subscriptionOfferDetails =
                    productDetails.subscriptionOfferDetails?.firstOrNull()
                val pricingPhase =
                    subscriptionOfferDetails?.pricingPhases?.pricingPhaseList?.firstOrNull()

                // 如果没有订阅优惠详情，跳过
                if (pricingPhase == null) {
                    LogUtils.w("Billing [价格更新] ⚠️ 商品 $planId 没有订阅优惠详情，跳过")
                    return@forEach
                }

                val formattedPrice = pricingPhase.formattedPrice
                val currencyCode = pricingPhase.priceCurrencyCode
                val micros = pricingPhase.priceAmountMicros
                val correctedPrice =
                    BillingUtils.correctCurrencySymbol(formattedPrice, currencyCode)

                LogUtils.d(
                    "Billing [价格更新] 处理商品: $planId (${currentPlan.name})\n" +
                        "  当前本地价格: ${currentPlan.price}\n" +
                        "  当前本地货币: ${currentPlan.currencyCode}\n" +
                        "  当前本地微单位: ${currentPlan.priceAmountMicros}\n" +
                        "  Google Play原始价格: $formattedPrice\n" +
                        "  Google Play货币代码: $currencyCode\n" +
                        "  Google Play微单位: $micros\n" +
                        "  修正后价格: $correctedPrice"
                )

                // 检查价格是否有变化
                // 如果当前价格为占位符"-"或空，强制更新
                val hasPlaceholder = currentPlan.price == "-" || currentPlan.price.isEmpty()
                val priceChanged = currentPlan.price != correctedPrice
                val currencyChanged = currentPlan.currencyCode != currencyCode
                val microsChanged = currentPlan.priceAmountMicros != micros

                val shouldUpdate =
                    hasPlaceholder || priceChanged || currencyChanged || microsChanged

                LogUtils.d(
                    "Billing [价格更新] 价格比较结果:\n" +
                        "  是否有占位符: $hasPlaceholder\n" +
                        "  价格是否变化: $priceChanged\n" +
                        "  货币是否变化: $currencyChanged\n" +
                        "  微单位是否变化: $microsChanged\n" +
                        "  是否需要更新: $shouldUpdate"
                )

                if (shouldUpdate) {
                    val oldPrice = currentPlan.price
                    val oldCurrency = currentPlan.currencyCode
                    val oldMicros = currentPlan.priceAmountMicros

                    updatedPlans[index] =
                        currentPlan.copy(
                            price = correctedPrice,
                            originalPrice = correctedPrice,
                            currencyCode = currencyCode,
                            priceAmountMicros = micros,
                        )
                    updatedCount++

                    LogUtils.i(
                        "Billing [价格更新] ✅ 价格已更新\n" +
                            "  商品ID: $planId\n" +
                            "  商品名称: ${currentPlan.name}\n" +
                            "  价格变化: $oldPrice -> $correctedPrice\n" +
                            "  货币变化: $oldCurrency -> $currencyCode\n" +
                            "  微单位变化: $oldMicros -> $micros"
                    )

                    // 上报Firebase：从Google Play获取到的订阅价格详细信息（100%采样）
                    try {
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.SUBSCRIPTION_PRICE_FETCHED,
                            mapOf(
                                "product_id" to planId,
                                "product_name" to (currentPlan.name ?: ""),
                                "plan_type" to (currentPlan.planType ?: ""),
                                "google_play_price" to formattedPrice,
                                "google_play_currency_code" to currencyCode,
                                "google_play_price_micros" to micros,
                                "corrected_price" to correctedPrice,
                                "old_price" to (oldPrice ?: "-"),
                                "old_currency_code" to (oldCurrency ?: ""),
                                "old_price_micros" to oldMicros,
                                "price_changed" to priceChanged,
                                "currency_changed" to currencyChanged,
                                "micros_changed" to microsChanged,
                            ),
                        )
                        LogUtils.d("Billing [价格更新] ✅ Firebase事件已上报: SUBSCRIPTION_PRICE_FETCHED")
                    } catch (e: Exception) {
                        LogUtils.e("Billing [价格更新] ⚠️ Firebase事件上报失败: ${e.message}")
                    }
                } else {
                    LogUtils.d("Billing [价格更新] ℹ️ 价格无变化，跳过: $planId (${currentPlan.name})")
                }
            } else {
                LogUtils.w("Billing [价格更新] ⚠️ 未找到匹配的计划ID: $planId")
                LogUtils.w("Billing [价格更新] 当前本地计划列表: ${updatedPlans.map { it.googleProductId }}")
            }
        }

        // 如果价格已更新，更新并保存到缓存
        if (updatedCount > 0) {
            LogUtils.i("Billing [价格更新] ✅ 检测到 $updatedCount 个计划价格变化，准备更新 plansFlow")
            LogUtils.d("Billing [价格更新] 更新后的计划列表:")
            updatedPlans.forEach { plan ->
                LogUtils.d(
                    "  - ${plan.googleProductId}: ${plan.name}, 价格=${plan.price}, 货币=${plan.currencyCode}, 微单位=${plan.priceAmountMicros}"
                )
            }

            plansFlow.value = updatedPlans
            LogUtils.i("Billing [价格更新] ✅ plansFlow 已更新")

            BillingStorage.saveLocalPlans(updatedPlans) // 保存到本地缓存（包含最新价格）
            LogUtils.i("Billing [价格更新] ✅ 价格信息已保存到本地缓存")
        } else {
            LogUtils.d("Billing [价格更新] ℹ️ 所有计划价格都无变化，无需更新")
        }
    }
}
