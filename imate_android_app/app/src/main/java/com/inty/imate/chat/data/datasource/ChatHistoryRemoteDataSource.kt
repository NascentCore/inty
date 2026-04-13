package com.inty.imate.chat.data.datasource

import com.ai.core.http.utils.get
import com.inty.imate.chat.data.bean.QueryMsgsResponse
import io.ktor.client.request.parameter
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatHistoryRemoteDataSource
@Inject
constructor() {

    suspend fun getMessages(
        agentId: String,
        limit: Int,
        offset: Int,
    ): QueryMsgsResponse {
        return get<QueryMsgsResponse>("/api/v1/chats/agents/$agentId/messages") {
            parameter("limit", limit)
            parameter("offset", offset)
            parameter("order", "desc")
        }
    }
}
