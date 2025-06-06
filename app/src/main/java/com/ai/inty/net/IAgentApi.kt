package com.ai.inty.net

import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.AgentInfoResponse
import com.ai.inty.beans.CreateGuestResult
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

@Singleton
interface IAgentApi {
    @GET("/api/v1/ai/agents")
    suspend fun agents(skip: Int, limit: Int): HttpResult<List<AgentInfo>>

//    @GET("/api/v1/recommendations/agents")
    @GET("api/v1/ai/agents/recommend")
    suspend fun recommendAgents(@Query("skip") skip: Int, @Query("limit")limit: Int): HttpResult<AgentInfoResponse>
}