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

@Singleton
interface IChatApi {
    @POST("/api/v1/chats/{agent_id}/messages")
    suspend fun sendMsg(@Body req: SendMsgReq): HttpResult<SendMsgResponse>

    @GET("/api/v1/chats/{agent_id}/messages")
    suspend fun getMsgs(@Body req: QueryMsgReq): HttpResult<QueryMsgsResponse>
}


