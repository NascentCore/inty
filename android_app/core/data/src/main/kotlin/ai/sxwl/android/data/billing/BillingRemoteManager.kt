package ai.sxwl.android.data.billing

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.TimeUtils
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow

/* 从后端获取订阅计划：
 * 获取订阅计划列表
 * 更新本地订阅状态
 * 更新本地订阅计划列表
 */
internal class BillingRemoteManager(
    private val vipStatusFlow: MutableStateFlow<VipStatus>,
    private val plansFlow: MutableStateFlow<List<VipPlan>>,
    private val priceManager: BillingPriceManager,
) {

    private val api = NetServiceMgr.getSubscriptionApi()

    /** 获取远程数据 */
    suspend fun fetchRemote(isConnected: Boolean) {

        runCatching { api.getSubscriptionPlans() }
            .onSuccess { result ->
                when (result) {
                    is HttpResult.Success -> {
                        val response = result.data
                        val currentSubscription = response.currentSubscription

                        // 更新会员状态
                        val isSubscribed = currentSubscription != null
                        val subscriptionId = currentSubscription?.planId
                        val purchaseTime =
                            TimeUtils.parseIsoTimeToTimestamp(currentSubscription?.startDate)
                        val expiryTime =
                            TimeUtils.parseIsoTimeToTimestamp(currentSubscription?.endDate)

                        val vipStatus =
                            VipStatus(
                                isSubscribed = isSubscribed,
                                subscriptionId = subscriptionId,
                                purchaseTime = purchaseTime,
                                expiryTime = expiryTime,
                                everSubscribed = response.has_ever_subscribed,
                                previous_plan_id = response.previous_plan_id,
                                // ACTIVE + auto_renew=true 是 "subscribed"；正常订阅，自动续费
                                // ACTIVE + auto_renew=false 是"subscribed_expiring"；正常订阅，不自动续费
                                // CANCELLED是"subscribed_expiring" 已取消但未到期
                                // null 认为是未订阅
                                subscriptionStatus =
                                    when (currentSubscription?.status) {
                                        "ACTIVE" if currentSubscription.autoRenew == true ->
                                            VipStatus.UI_SUBSCRIBED

                                        "ACTIVE" if currentSubscription.autoRenew == false ->
                                            VipStatus.UI_SUBSCRIBED_EXPIRE_SOON

                                        "CANCELLED" ->
                                            VipStatus.UI_SUBSCRIBED_EXPIRE_SOON

                                        else -> VipStatus.UI_UNSUBSCRIBED
                                    },
                            )

                        // 保存到本地并更新Flow
                        BillingStorage.saveLocalVipStatus(vipStatus)
                        vipStatusFlow.value = vipStatus

                        // 更新订阅计划列表
                        // 保留现有价格信息，避免覆盖
                        LogUtils.i("Billing [远程数据] 开始更新订阅计划列表，后端返回 ${response.plans.size} 个计划")

                        val existingPlans = plansFlow.value.associateBy { it.googleProductId }
                        LogUtils.d("Billing [远程数据] 当前本地计划数量: ${existingPlans.size}")
                        existingPlans.values.forEach { plan ->
                            LogUtils.d("  - ${plan.googleProductId}: ${plan.name}, 价格=${plan.price}, 货币=${plan.currencyCode}")
                        }

                        val vipPlans =
                            response.plans.mapNotNull { plan ->
                                plan.googlePlayProductId?.let { productId ->
                                    // 如果已存在该计划，保留其价格信息
                                    existingPlans[productId]?.let { existingPlan ->
                                        LogUtils.d(
                                            "Billing [远程数据] 保留现有计划的价格信息: $productId\n" +
                                                    "  保留的价格: ${existingPlan.price}\n" +
                                                    "  保留的货币: ${existingPlan.currencyCode}\n" +
                                                    "  保留的微单位: ${existingPlan.priceAmountMicros}"
                                        )
                                        // 更新计划的基础信息，但保留价格信息
                                        existingPlan.copy(
                                            discountRate = plan.discountRate
                                                ?: existingPlan.discountRate,
                                            name = plan.name ?: existingPlan.name,
                                            planType = plan.planType ?: existingPlan.planType,
                                            description = plan.description
                                                ?: existingPlan.description,
                                        )
                                    } ?: run {
                                        LogUtils.d("Billing [远程数据] 新计划（无价格信息）: $productId, ${plan.name}")
                                        VipPlan(
                                            // 新计划，使用默认值
                                            googleProductId = productId,
                                            discountRate = plan.discountRate ?: 1.0,
                                            name = plan.name ?: "",
                                            planType = plan.planType ?: "",
                                            description = plan.description ?: "",
                                        )
                                    }
                                }
                            }

                        LogUtils.i("Billing [远程数据] 计划列表更新完成，共 ${vipPlans.size} 个计划")
                        // 更新plansFlow，但先不保存到缓存（等待价格更新后再保存）
                        plansFlow.value = vipPlans

                        // 如果 BillingClient 已连接，立即查询价格
                        if (isConnected) {
                            LogUtils.i("Billing [远程数据] BillingClient 已连接，立即查询价格")
                            priceManager.queryProductDetails(isConnected)
                        } else {
                            LogUtils.w("Billing [远程数据] BillingClient 未连接，等待连接成功后查询价格")
                            // 如果未连接，暂时保存基础信息到缓存（不包含价格）
                            // 等连接成功后再更新价格
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("Billing 获取订阅计划失败: ${result.message}")
                    }
                }
            }
            .onFailure { exception ->
                when (exception) {
                    is CancellationException -> {
                        LogUtils.w("Billing 获取订阅计划被取消: ${exception.message}")
                    }

                    else -> {
                        LogUtils.e("Billing 获取订阅计划异常: ${exception.message}")
                    }
                }
            }
    }
}
