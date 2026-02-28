package ai.sxwl.android.data.api

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.ChatImageGenerationApiResponse
import ai.sxwl.android.data.api.model.ChatImageGenerationRequest
import ai.sxwl.android.data.api.model.ChatMusicGenerationApiResponse
import ai.sxwl.android.data.api.model.ChatMusicGenerationRequest
import ai.sxwl.android.data.api.model.ChatSettingsReq
import ai.sxwl.android.data.api.model.ChatSettingsResponse
import ai.sxwl.android.data.api.model.ClearMessagesRequest
import ai.sxwl.android.data.api.model.ClearMessagesResponse
import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.api.model.MsgVoiceRsp
import ai.sxwl.android.data.api.model.QueryMsgsResponse
import ai.sxwl.android.data.api.model.SendMsgReq
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.api.model.SurpriseSnapUnlockReq
import ai.sxwl.android.data.api.model.SurpriseSnapUnlockResp
import ai.sxwl.android.data.api.model.VoteMessageReq
import ai.sxwl.android.data.api.model.VoteMessageRsp
import com.architecture.httplib.core.HttpResult
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface IChatApi {

    @POST("/api/v1/chats/surprise-snap/unlock")
    suspend fun unlockSurpriseSnap(
        @Body req: SurpriseSnapUnlockReq
    ): HttpResult<SurpriseSnapUnlockResp>

    @POST("/api/v1/chat/completions/{agent_id}")
    suspend fun sendMsg(
        @Path("agent_id") agent_id: String,
        @Body req: SendMsgReq,
    ): HttpResult<SendMsgResponse>

    @GET("/api/v1/chats/agents/{agent_id}/messages")
    suspend fun getMsgs(
        @Path("agent_id") agent_id: String,
        @Query("limit") limit: Int,
        @Query("offset") offset: Int,
        @Query("order") order: String = "desc",
    ): HttpResult<QueryMsgsResponse>

    @GET("/api/v1/chats/")
    suspend fun getConversations(
        @Query("skip") skip: Int,
        @Query("limit") limit: Int,
    ): HttpResult<List<ConversationItem>>

    @GET("/api/v1/ai/agents/{agent_id}")
    suspend fun getAgentInfo(@Path("agent_id") agent_id: String): HttpResult<AgentInfo>

    @GET("/api/v1/chats/agents/{agent_id}/settings")
    suspend fun getChatSettings(
        @Path("agent_id") agent_id: String
    ): HttpResult<ChatSettingsResponse.ChatSettingRspData>

    @PUT("/api/v1/chats/agents/{agent_id}/settings")
    suspend fun updateChatSettings(
        @Path("agent_id") agent_id: String,
        @Body req: ChatSettingsReq,
    ): HttpResult<ChatSettingsResponse>

    @POST("/api/v1/chats/agents/{agent_id}/messages/{message_id}/voice")
    suspend fun fetchMsgVoice(
        @Path("agent_id") agent_id: String,
        @Path("message_id") message_id: String,
    ): HttpResult<MsgVoiceRsp>

    @POST("/api/v1/chats/messages/vote")
    suspend fun voteMessage(@Body req: VoteMessageReq): HttpResult<VoteMessageRsp>

    @POST("/api/v1/chat/images/{agent_id}")
    suspend fun generateMessageImage(
        @Path("agent_id") agent_id: String,
        @Body req: ChatImageGenerationRequest,
    ): HttpResult<ChatImageGenerationApiResponse>

    @POST("/api/v1/chat/music/{agent_id}")
    suspend fun generateMessageMusic(
        @Path("agent_id") agent_id: String,
        @Body req: ChatMusicGenerationRequest,
    ): HttpResult<ChatMusicGenerationApiResponse>

    @POST("/api/v1/chats/agents/{agent_id}/clear-messages")
    suspend fun clearMessages(
        @Path("agent_id") agent_id: String,
        @Body req: ClearMessagesRequest,
    ): HttpResult<ClearMessagesResponse>
}
