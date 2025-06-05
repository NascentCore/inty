package com.ai.inty.net

import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.CreateGuestResult
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.GET

@Singleton
interface IAgentApi {
    @GET("/api/v1/ai/agents")
    suspend fun agents(skip: Int, limit: Int): HttpResult<List<AgentInfo>>
}