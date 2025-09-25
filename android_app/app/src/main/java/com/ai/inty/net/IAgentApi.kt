package com.ai.inty.net

import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.AgentInfoResponse
import com.ai.inty.beans.CreateAgentRequest
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
    suspend fun recommendAgents(
        @Query("page") page: Int,
        @Query("page_size") pageSize: Int,
        @Query("sort_seed")
        sort_seed: String, // 随机排序的时候，这里需要一个随机种子，每一批次的请求，随机种子一致（即 同一个下载刷新后的加载更多，他们是一批次）
        @Query("sort")
        sort: String =
            "score_based_random", // 四种排序 created_asc, created_desc, random, score_based_random
    ): HttpResult<AgentInfoResponse>

    @POST("/api/v1/ai/agents")
    suspend fun createAgent(@Body request: CreateAgentRequest): HttpResult<AgentInfo>

    @GET("/api/v1/ai/agents/me")
    suspend fun getUserCreatedAgents(
        @Query("skip") skip: Int,
        @Query("limit") limit: Int,
    ): HttpResult<List<AgentInfo>>

    @POST("/api/v1/ai/agents/text-to-image")
    suspend fun generateBackground(
        @Body request: GenerateBackgroundRequest
    ): HttpResult<GenerateBackgroundResponse>

    @GET("/api/v1/ai/agents/{agentId}")
    suspend fun getAgentDetail(@Path("agentId") agentId: String): HttpResult<AgentInfo>

    @PUT("/api/v1/ai/agents/{agentId}")
    suspend fun updateAgent(
        @Path("agentId") agentId: String,
        @Body request: CreateAgentRequest,
    ): HttpResult<AgentInfo>

    @DELETE("/api/v1/ai/agents/{agentId}")
    suspend fun deleteAgent(@Path("agentId") agentId: String): HttpResult<AgentInfo>

    @Multipart
    @POST("/api/v1/images")
    suspend fun uploadAvatar(@Part file: MultipartBody.Part): HttpResult<UploadAvatarResponse>
}
