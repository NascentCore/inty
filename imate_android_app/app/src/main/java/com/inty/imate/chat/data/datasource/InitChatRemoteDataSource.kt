package com.inty.imate.chat.data.datasource

import com.inty.imate.chat.data.bean.AgentInfo
import com.inty.imate.chat.data.bean.CreateAgentRequest
import com.inty.imate.chat.data.bean.GenerateAvatarRequest
import com.inty.imate.chat.data.bean.GenerateAvatarResponse
import com.ai.core.http.utils.get
import com.ai.core.http.utils.post
import io.ktor.client.request.setBody
import javax.inject.Inject

class InitChatRemoteDataSource @Inject constructor() {
    suspend fun generateAvatar(prompt: String): GenerateAvatarResponse {
        return post<GenerateAvatarResponse>("/api/v1/ai/agents/text-to-image") {
            setBody(GenerateAvatarRequest(prompt = prompt))
        }
    }

    suspend fun createAgent(request: CreateAgentRequest): AgentInfo {
        return post<AgentInfo>("/api/v1/ai/agents") {
            setBody(request)
        }
    }

    suspend fun getAgent(agentId: String): AgentInfo {
        return get<AgentInfo>("/api/v1/ai/agents/${agentId}")
    }
}

