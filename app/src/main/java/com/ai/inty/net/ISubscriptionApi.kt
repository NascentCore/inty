package com.ai.inty.net

import com.ai.inty.beans.SubscriptionPlansResponse
import com.architecture.httplib.core.HttpResult
import retrofit2.http.GET

/**
 * 订阅计划相关API接口
 */
interface ISubscriptionApi {
    
    /**
     * 获取订阅计划列表
     * GET /api/v1/subscription/plans
     * 
     * @return 订阅计划列表响应
     */
    @GET("api/v1/subscription/plans")
    suspend fun getSubscriptionPlans(): HttpResult<SubscriptionPlansResponse>
} 