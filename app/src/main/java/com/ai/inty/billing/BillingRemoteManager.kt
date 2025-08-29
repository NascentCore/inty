package com.ai.inty.billing

import com.ai.inty.net.ISubscriptionApi
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.flow.MutableStateFlow

/**
 * 计费远程数据管理类
 */
internal class BillingRemoteManager(
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
        EasyLog.log("BillingRepository BillingRemoteManager - 开始获取远程数据")
        
        runCatching { api.getSubscriptionPlans() }
            .onSuccess { result ->
                when (result) {
                    is HttpResult.Success -> {
                        val response = result.data
                        val currentSubscription = response.currentSubscription

                        // 更新会员状态
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

                        EasyLog.log("BillingRepository BillingRemoteManager 会员状态更新: isSubscribed=$isSubscribed, subscriptionId=$subscriptionId")

                        // 保存到本地并更新Flow
                        BillingStorage.saveLocalVipStatus(vipStatus)
                        vipStatusFlow.value = vipStatus

                        // 更新订阅计划列表
                        val vipPlans = response.plans.mapNotNull { plan ->
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

                        EasyLog.log("BillingRepository BillingRemoteManager 订阅计划更新: 获取到 ${vipPlans.size} 个计划")
                        EasyLog.log(
                            "BillingRepository BillingRemoteManager 订阅计划更新: 获取到 ${
                                vipPlans.joinToString(
                                    " ,, "
                                )
                            } 个计划"
                        )

                        // 直接更新plansFlow，不进行复杂的变化检测
                        BillingStorage.saveLocalPlans(vipPlans)
                        plansFlow.value = vipPlans

                        // 如果 BillingClient 已连接，立即查询价格
                        if (isConnected) {
                            EasyLog.log("BillingRepository BillingRemoteManager BillingClient 已连接，立即查询价格信息")
                            priceManager.querySkuDetails(isConnected)
                        } else {
                            EasyLog.log("BillingRepository BillingRemoteManager BillingClient 未连接，等待连接成功后查询价格")
                        }
                    }

                    is HttpResult.Failure -> {
                        EasyLog.log("BillingRepository BillingRemoteManager 获取订阅计划失败: ${result.message}")
                    }
                }
            }
            .onFailure { exception ->
                when (exception) {
                    is kotlinx.coroutines.CancellationException -> {
                        EasyLog.log("BillingRepository BillingRemoteManager 获取订阅计划被取消: ${exception.message}")
                    }
                    else -> {
                        EasyLog.log("BillingRepository BillingRemoteManager 获取订阅计划异常: ${exception.message}")
                    }
                }
            }
    }
} 
