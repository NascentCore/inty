package com.ai.inty.net

import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.ChatSettingsReq
import com.ai.inty.beans.ChatSettingsResponse
import com.ai.inty.beans.ConversationItem
import com.ai.inty.beans.MsgVoiceRsp
import com.ai.inty.beans.QueryMsgsResponse
import com.ai.inty.beans.SendMsgReq
import com.ai.inty.beans.SendMsgResponse
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

@Singleton
interface IChatApi {
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
}
