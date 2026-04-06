package ai.sxwl.android.data.api

import ai.sxwl.android.data.api.model.AgentEnergyPointsUpdateRequest
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AgentInfoResponse
import ai.sxwl.android.data.api.model.CharacterThemeItem
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.data.api.model.GenerateBackgroundRequest
import ai.sxwl.android.data.api.model.GenerateBackgroundResponse
import ai.sxwl.android.data.api.model.UploadAvatarResponse
import com.architecture.httplib.core.HttpResult
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

interface IAgentApi {

    /** 用于explore页面的列表数据 */
    @GET("api/v1/ai/agents/recommend")
    suspend fun exploreAgents(
        @Query("page") page: Int,
        @Query("page_size") pageSize: Int,
        @Query("sort_seed")
        sort_seed: String, // 随机排序的时候，这里需要一个随机种子，每一批次的请求，随机种子一致（即 同一个下载刷新后的加载更多，他们是一批次）
        @Query("sort")
        sort: String =
            "score_based_random", // 四种排序 created_asc, created_desc, random, score_based_random
    ): HttpResult<AgentInfoResponse>

    /** 用于首页chat列表的agents数据 */
    @GET("api/v1/ai/agents/recommend")
    suspend fun chatAgents(
        @Query("page") page: Int,
        @Query("page_size") pageSize: Int,
        @Query("sort_seed")
        sort_seed: String, // 随机排序的时候，这里需要一个随机种子，每一批次的请求，随机种子一致（即 同一个下载刷新后的加载更多，他们是一批次）
        @Query("sort")
        sort: String =
            "score_based_random", // 四种排序 created_asc, created_desc, random, score_based_random
    ): HttpResult<AgentInfoResponse>

    @GET("api/v1/ai/agents/recommend")
    suspend fun boostLeaderboardAgents(
        @Query("page") page: Int,
        @Query("page_size") pageSize: Int,
        @Query("sort_seed") sortSeed: String,
        @Query("sort") sort: String = "energy_points",
    ): HttpResult<AgentInfoResponse>

    /** Text-to-image description match: sort by fuzzy similarity; optional match_description + match_top_n. */
    @GET("api/v1/ai/agents/recommend")
    suspend fun recommendAgentsByImageDescription(
        @Query("page") page: Int,
        @Query("page_size") pageSize: Int,
        @Query("sort") sort: String = "text_match_image_description",
        @Query("match_description") matchDescription: String,
        @Query("match_top_n") matchTopN: Int,
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

    @PUT("/api/v1/ai/agents/{agentId}")
    suspend fun updateAgentEnergyPoints(
        @Path("agentId") agentId: String,
        @Body request: AgentEnergyPointsUpdateRequest,
    ): HttpResult<AgentInfo>

    @DELETE("/api/v1/ai/agents/{agentId}")
    suspend fun deleteAgent(@Path("agentId") agentId: String): HttpResult<AgentInfo>

    @Multipart
    @POST("/api/v1/images")
    suspend fun uploadAvatar(@Part file: MultipartBody.Part): HttpResult<UploadAvatarResponse>

    @GET("/api/v1/character-themes/")
    suspend fun getCharacterThemes(
        @Query("skip") skip: Int,
        @Query("limit") limit: Int,
    ): HttpResult<List<CharacterThemeItem>>
}
