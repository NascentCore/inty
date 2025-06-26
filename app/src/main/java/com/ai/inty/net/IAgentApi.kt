package com.ai.inty.net

import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.AgentInfoResponse
import com.ai.inty.beans.CreateAgentRequest
import com.ai.inty.beans.CreateAgentResponse
import com.ai.inty.beans.CreateGuestResult
import com.ai.inty.beans.FollowResponse
import com.ai.inty.beans.GenerateBackgroundRequest
import com.ai.inty.beans.GenerateBackgroundResponse
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

@Singleton
interface IAgentApi {
    @GET("/api/v1/ai/agents")
    suspend fun agents(skip: Int, limit: Int): HttpResult<List<AgentInfo>>

//    @GET("/api/v1/recommendations/agents")
    @GET("api/v1/ai/agents/recommend")
    suspend fun recommendAgents(@Query("page") page: Int, @Query("page_size")pageSize: Int): HttpResult<AgentInfoResponse>
    
    @GET("/api/v1/ai/agents/following")
    suspend fun getFollowingAgents(@Query("page") page: Int, @Query("page_size") pageSize: Int): HttpResult<AgentInfoResponse>
    
    @POST("/api/v1/ai/agents/{agentId}/follow")
    suspend fun followAgent(@Path("agentId") agentId: String): HttpResult<FollowResponse>
    
    @DELETE("/api/v1/ai/agents/{agentId}/follow")
    suspend fun unfollowAgent(@Path("agentId") agentId: String): HttpResult<FollowResponse>
    
    @POST("/api/v1/ai/agents/")
    suspend fun createAgent(@Body request: CreateAgentRequest): HttpResult<AgentInfo>
    
    @GET("/api/v1/ai/agents/")
    suspend fun getUserCreatedAgents(@Query("skip") skip: Int, @Query("limit") limit: Int): HttpResult<List<AgentInfo>>
    
    @POST("/api/v1/ai/agents/generate_background")
    suspend fun generateBackground(@Body request: GenerateBackgroundRequest): HttpResult<GenerateBackgroundResponse>
}