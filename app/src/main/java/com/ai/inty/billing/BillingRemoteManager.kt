package com.ai.inty.billing

import com.ai.inty.net.ISubscriptionApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.flow.MutableStateFlow

/**
 * 计费远程数据管理类
 */
class BillingRemoteManager(
    private val vipStatusFlow: MutableStateFlow<VipStatus>,
    private val plansFlow: MutableStateFlow<List<VipPlan>>,
    private val priceManager: BillingPriceManager
) {

    private val api = TheRouter.get(ISubscriptionApi::class.java)
        ?: error("Billing Remote Manager theRouter init Error")

    /**
     * 获取远程数据
     */
    suspend fun fetchRemote(isConnected: Boolean) {
        runCatching { api.getSubscriptionPlans() }
            .onSuccess { result ->
                when (result) {
                    is HttpResult.Success -> {
                        val response = result.data
                        val currentSubscription = response.currentSubscription

                        // 根据currentSubscription是否为空判断会员状态
                        val isSubscribed = currentSubscription != null
                        val subscriptionId = currentSubscription?.planId
                        val purchaseTime = currentSubscription?.startDate?.toLongOrNull() ?: 0L
                        val expiryTime = currentSubscription?.endDate?.toLongOrNull() ?: 0L

                        val vipStatus = VipStatus(
                            isSubscribed = isSubscribed,
                            subscriptionId = subscriptionId,
                            purchaseTime = purchaseTime,
                            expiryTime = expiryTime,
                            everSubscribed = response.has_ever_subscribed,
                            previous_plan_id = response.previous_plan_id
                        )

                        EasyLog.log("会员状态更新: isSubscribed=$isSubscribed, subscriptionId=$subscriptionId")
                        BillingStorage.saveLocalVipStatus(vipStatus)
                        vipStatusFlow.value = vipStatus

                        // 更新订阅计划列表
                        val vipPlans = response.plans.mapNotNull { plan ->
                            // 过滤掉没有googlePlayProductId的计划
                            plan.googlePlayProductId?.let { productId ->
                                VipPlan(
                                    googleProductId = productId,
                                    discountRate = plan.discountRate ?: 1.0,
                                    name = plan.name ?: "",
                                    planType = plan.planType ?: "",
                                    description = plan.description ?: ""
                                )
                            }
                        }
                        EasyLog.log("订阅计划更新: 获取到 ${vipPlans.size} 个计划")

                        // 检查是否有实际变化
                        val currentPlans = plansFlow.value
                        val hasChanges = BillingUtils.checkPlansChanged(currentPlans, vipPlans)

                        if (hasChanges) {
                            EasyLog.log("检测到计划数据变化，更新 plansFlow")
                            BillingStorage.saveLocalPlans(vipPlans)
                            plansFlow.value = vipPlans

                            // 如果 BillingClient 已连接，立即查询价格
                            if (isConnected) {
                                EasyLog.log("BillingClient 已连接，立即查询价格信息")
                                priceManager.querySkuDetails(isConnected)
                            } else {
                                EasyLog.log("BillingClient 未连接，等待连接成功后查询价格")
                            }
                        } else {
                            EasyLog.log("计划数据无变化，跳过更新")

                            // 即使数据无变化，如果 BillingClient 已连接且 plansFlow 为空，也要查询价格
                            if (isConnected && plansFlow.value.isEmpty()) {
                                EasyLog.log("plansFlow 为空但 BillingClient 已连接，查询价格信息")
                                priceManager.querySkuDetails(isConnected)
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log("获取订阅计划失败: ${result.message}")
                    }
                }
            }
            .onFailure { exception ->
                when (exception) {
                    is kotlinx.coroutines.CancellationException -> {
                        EasyLog.log("获取订阅计划被取消: ${exception.message}")
                        // 协程被取消是正常情况，不需要特殊处理
                    }

                    else -> {
                        EasyLog.log("获取订阅计划异常: ${exception.message}")
                    }
                }
            }
    }
} 
