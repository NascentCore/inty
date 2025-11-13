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

    /** 用户订阅信息数据类 */
    data class UserSubscription(
        val id: String,
        val planId: String,
        val status: String,
        val startDate: Long,
        val endDate: Long,
        val isActive: Boolean,
    )
}
