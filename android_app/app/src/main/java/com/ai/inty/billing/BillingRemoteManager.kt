package com.ai.inty.billing

import com.ai.inty.net.ISubscriptionApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.inty.utils.parseIsoTimeToTimestamp
import com.therouter.TheRouter
import kotlinx.coroutines.flow.MutableStateFlow

/** 计费远程数据管理类 */
internal class BillingRemoteManager(
    private val vipStatusFlow: MutableStateFlow<VipStatus>,
    private val plansFlow: MutableStateFlow<List<VipPlan>>,
    private val priceManager: BillingPriceManager,
) {

    private val api =
        TheRouter.get(ISubscriptionApi::class.java)
            ?: error("Billing Remote Manager theRouter init Error")

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
                        val purchaseTime = parseIsoTimeToTimestamp(currentSubscription?.startDate)
                        val expiryTime = parseIsoTimeToTimestamp(currentSubscription?.endDate)

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
                                    when {
                                        currentSubscription?.status == "ACTIVE" &&
                                            currentSubscription.autoRenew == true ->
                                            VipStatus.UI_SUBSCRIBED

                                        currentSubscription?.status == "ACTIVE" &&
                                            currentSubscription.autoRenew == false ->
                                            VipStatus.UI_SUBSCRIBED_EXPIRE_SOON

                                        currentSubscription?.status == "CANCELLED" ->
                                            VipStatus.UI_SUBSCRIBED_EXPIRE_SOON

                                        else -> VipStatus.UI_UNSUBSCRIBED
                                    },
                            )

                        // 保存到本地并更新Flow
                        BillingStorage.saveLocalVipStatus(vipStatus)
                        vipStatusFlow.value = vipStatus

                        // 更新订阅计划列表
                        val vipPlans =
                            response.plans.mapNotNull { plan ->
                                plan.googlePlayProductId?.let { productId ->
                                    VipPlan(
                                        googleProductId = productId,
                                        discountRate = plan.discountRate ?: 1.0,
                                        name = plan.name ?: "",
                                        planType = plan.planType ?: "",
                                        description = plan.description ?: "",
                                    )
                                }
                            }

                        // 直接更新plansFlow，不进行复杂的变化检测
                        BillingStorage.saveLocalPlans(vipPlans)
                        plansFlow.value = vipPlans

                        // 如果 BillingClient 已连接，立即查询价格
                        if (isConnected) {
                            priceManager.querySkuDetails()
                        } else {
                            EasyLog.log(
                                "BillingRepository BillingRemoteManager BillingClient 未连接，等待连接成功后查询价格",
                                EasyLog.WARN,
                            )
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log(
                            "BillingRepository BillingRemoteManager 获取订阅计划失败: ${result.message}",
                            EasyLog.ERROR,
                        )
                    }
                }
            }
            .onFailure { exception ->
                when (exception) {
                    is kotlinx.coroutines.CancellationException -> {
                        EasyLog.log(
                            "BillingRepository BillingRemoteManager 获取订阅计划被取消: ${exception.message}",
                            EasyLog.ERROR,
                        )
                    }

                    else -> {
                        EasyLog.log(
                            "BillingRepository BillingRemoteManager 获取订阅计划异常: ${exception.message}",
                            EasyLog.ERROR,
                        )
                    }
                }
            }
    }
}
