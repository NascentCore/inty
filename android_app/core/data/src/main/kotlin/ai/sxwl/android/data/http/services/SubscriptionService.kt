package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.model.SubscriptionPlan
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager

/** 订阅服务 封装所有订阅相关的API调用 替换原有的 ISubscriptionApi */
object SubscriptionService {

    /** 获取订阅计划列表 替换: ISubscriptionApi.getSubscriptionPlans() */
    suspend fun getSubscriptionPlans(): ApiResult<List<SubscriptionPlan>> {
        return IntyNetworkManager.executeRequest("Get Subscription Plans") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .subscription()
                    .listPlans()

            val plans = response.data()?.plans() ?: emptyList()
            plans.map { plan ->
                val featuresMap = plan.features()?.let { features ->
                    val map = mutableMapOf<String, Any>()
                    features._additionalProperties().forEach { (key, value) ->
                        when {
                            value.asString() != null -> map[key] = value.asString()!!
                            value.asNumber() != null -> map[key] = value.asNumber()!!
                            value.asBoolean() != null -> map[key] = value.asBoolean()!!
                            else -> map[key] = value.toString()
                        }
                    }
                    map
                }
                SubscriptionPlan(
                    id = plan.id(),
                    name = plan.name(),
                    description = plan.description(),
                    price = plan.price(),
                    currency = plan.currency(),
                    planType = plan.planType().toString(),
                    googlePlayProductId = plan.googlePlayProductId(),
                    discountRate = plan.discountRate(),
                    features = featuresMap,
                    chatLimitPerDay = plan.chatLimitPerDay()?.toInt(),
                    agentCreationLimit = plan.agentCreationLimit()?.toInt(),
                    isActive = plan.isActive(),
                    sortOrder = plan.sortOrder()?.toInt(),
                    createdAt = plan.createdAt().toString(),
                    updatedAt = plan.updatedAt()?.toString(),
                )
            }
        }
    }

    /** 获取用户订阅信息 替换: ISubscriptionApi.getUserSubscription() */
    suspend fun getUserSubscription(): ApiResult<UserSubscription> {
        return IntyNetworkManager.executeRequest("Get User Subscription") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .subscription()
                    .getStatus()

            val data = response.data()
            val subscription = data?.subscription()
            UserSubscription(
                id = subscription?.id() ?: "",
                planId = subscription?.planId() ?: "",
                status = subscription?.status()?.toString() ?: data?.subscriptionStatus() ?: "",
                startDate = subscription?.startDate()?.toEpochSecond() ?: 0L,
                endDate = subscription?.endDate()?.toEpochSecond() ?: 0L,
                isActive = data?.isSubscribed() ?: false,
            )
        }
    }

    /** 创建订阅 替换: ISubscriptionApi.createSubscription() */
    suspend fun createSubscription(planId: String): ApiResult<SubscriptionResult> {
        return IntyNetworkManager.executeRequest("Create Subscription") {
            // 当前 IntySDK 没有直接的 subscription creation API
            // 等 API 完善后再实现
            throw Exception("Subscription creation not supported, check API documentation")
        }
    }

    /** 取消订阅 替换: ISubscriptionApi.cancelSubscription() */
    suspend fun cancelSubscription(subscriptionId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Cancel Subscription") {
            // 当前 IntySDK 没有直接的 cancel subscription API
            // 等 API 完善后再实现
            throw Exception("Cancel subscription not supported, check API documentation")
        }
    }

    /** 更新订阅 替换: ISubscriptionApi.updateSubscription() */
    suspend fun updateSubscription(
        subscriptionId: String,
        planId: String,
    ): ApiResult<SubscriptionResult> {
        return IntyNetworkManager.executeRequest("Update Subscription") {
            // 当前 IntySDK 没有直接的 subscription update API
            // 等 API 完善后再实现
            throw Exception("Subscription update not supported, check API documentation")
        }
    }

    /** 验证订阅状态 替换: ISubscriptionApi.validateSubscription() */
    suspend fun validateSubscription(
        purchaseToken: String,
        productId: String,
    ): ApiResult<Boolean> {
        return IntyNetworkManager.executeRequest("Validate Subscription") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .subscription()
                    .verify(
                        com.inty.api.models.api.v1.subscription.SubscriptionVerifyParams.builder()
                            .purchaseToken(purchaseToken)
                            .productId(productId)
                            .build()
                    )

            response.data()?.isVerified() ?: false
        }
    }

    /** 获取使用统计 */
    suspend fun getUsage(): ApiResult<UsageStatistics> {
        return IntyNetworkManager.executeRequest("Get Usage Statistics") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .subscription()
                    .getUsage()

            val usage = response.data()
            UsageStatistics(
                imageGenerationCount = 0, // SDK中没有直接的imageGenerationCount字段
                imageGenerationLimit = 0, // SDK中没有直接的imageGenerationLimit字段
                voiceGenerationCount = 0, // SDK中没有直接的voiceGenerationCount字段
                voiceGenerationLimit = 0, // SDK中没有直接的voiceGenerationLimit字段
            )
        }
    }

    /** 用户订阅信息数据类 */
    data class UserSubscription(
        val id: String,
        val planId: String,
        val status: String,
        val startDate: Long,
        val endDate: Long,
        val isActive: Boolean,
    )

    /** 订阅结果数据类 */
    data class SubscriptionResult(
        val subscriptionId: String,
        val status: String,
        val paymentUrl: String?,
    )

    /** 使用统计数据类 */
    data class UsageStatistics(
        val imageGenerationCount: Int,
        val imageGenerationLimit: Int,
        val voiceGenerationCount: Int,
        val voiceGenerationLimit: Int,
    )
}
