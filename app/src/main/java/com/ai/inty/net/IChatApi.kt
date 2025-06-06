package com.ai.inty.net

import com.ai.inty.beans.QueryMsgReq
import com.ai.inty.beans.QueryMsgsResponse
import com.ai.inty.beans.SendMsgReq
import com.ai.inty.beans.SendMsgResponse
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

@Singleton
interface IChatApi {
    @POST("/api/v1/chats/agents/{agent_id}/chat/completions")
    suspend fun sendMsg(@Path("agent_id") agent_id: String, @Body req: SendMsgReq): HttpResult<SendMsgResponse>

    @GET("/api/v1/chats/agents/{agent_id}/messages")
    suspend fun getMsgs(@Path("agent_id") agent_id: String, @Query("limit")limit: Int, @Query("offset") offset: Int, @Query("order") order: String = "desc"): HttpResult<QueryMsgsResponse>
}


