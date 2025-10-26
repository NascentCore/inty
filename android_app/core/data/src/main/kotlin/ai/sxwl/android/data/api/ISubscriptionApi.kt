package ai.sxwl.android.data.api

import ai.sxwl.android.data.api.model.SubscriptionPlansResponse
import ai.sxwl.android.data.api.model.SubscriptionVerifyRequest
import ai.sxwl.android.data.api.model.SubscriptionVerifyResponse
import com.architecture.httplib.core.HttpResult
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

/** 订阅计划相关API接口 */
interface ISubscriptionApi {
    /**
     * 获取订阅计划列表 GET /api/v1/subscription/plans
     *
     * @return 订阅计划列表响应
     */
    @GET("api/v1/subscription/plans")
    suspend fun getSubscriptionPlans(): HttpResult<SubscriptionPlansResponse>

    /**
     * 验证订阅信息 POST /api/v1/subscription/verify
     *
     * @param request 订阅验证请求，包含 product_id、purchase_token 和 order_id
     * @return 订阅验证响应
     */
    @POST("api/v1/subscription/verify")
    suspend fun verifySubscription(
        @Body request: SubscriptionVerifyRequest,
    ): HttpResult<SubscriptionVerifyResponse>
}
