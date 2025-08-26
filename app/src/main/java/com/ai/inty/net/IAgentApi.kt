package com.ai.inty.net

import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.AgentInfoResponse
import com.ai.inty.beans.CreateAgentRequest
import com.ai.inty.beans.FollowResponse
import com.ai.inty.beans.GenerateBackgroundRequest
import com.ai.inty.beans.GenerateBackgroundResponse
import com.ai.inty.beans.UploadAvatarResponse
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

@Singleton
interface IAgentApi {

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
    
    @GET("/api/v1/ai/agents/{agentId}")
    suspend fun getAgentDetail(@Path("agentId") agentId: String): HttpResult<AgentInfo>
    
    @PUT("/api/v1/ai/agents/{agentId}")
    suspend fun updateAgent(@Path("agentId") agentId: String, @Body request: CreateAgentRequest): HttpResult<AgentInfo>
    
    @DELETE("/api/v1/ai/agents/{agentId}")
    suspend fun deleteAgent(@Path("agentId") agentId: String): HttpResult<AgentInfo>
    
    @Multipart
    @POST("/api/v1/ai/agents/upload-avatar")
    suspend fun uploadAvatar(@Part file: MultipartBody.Part): HttpResult<UploadAvatarResponse>
}
